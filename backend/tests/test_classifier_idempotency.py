"""Integration tests Phase 09 — runner idempotent/resumable + progress API.

⚠️ Marker `integration` — chạy riêng: `uv run pytest -m integration`
(DB Supabase thật cho feedbacks/analysis_runs; internet cần cho login seed).

Nguyên tắc an toàn chi phí: MỌI test trong file này đều có autouse fixture
gắn FakeClassifier + fake embedder — không một call LLM/embeddings THẬT nào
có thể phát sinh dù runner chạm phải row lạ trên DB dùng chung.

Kịch bản chính theo plan §3.3:
- Seed 10 feedbacks (created_at so le để ORDER BY created_at deterministic);
- Crash giả lập ở item 5 (RuntimeError — ngoài `_ITEM_ERRORS` nên giết batch)
  → run failed, 4 item có labels;
- Gọi lại `run_analysis` CÙNG run (resume — quyết định ghi decisions.md
  2026-08-24) → 6 item còn lại xử lý, tổng classify success ĐÚNG = 10
  (không phải 14) — mỗi item được classify ĐÚNG MỘT LẦN;
- requires_human_review khớp công thức HITL trên từng item mock;
- processed_count monotonic (4 → 10, không vượt total).
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs import analysis_runner as runner_mod
from app.jobs.analysis_runner import run_analysis
from app.models.analysis_run import AnalysisRun
from app.models.enums import ReviewStatus, RunStatus
from app.models.feedback import Feedback
from app.schemas.taxonomy import Classification
from app.services import classifier as classifier_mod
from app.models.enums import UserRole
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

SOURCE = "test-runner9"
REF_PREFIX = "runner9-"
N_ITEMS = 10
CRASH_ITEM = 5  # plan §3.3: crash sau item 4 → raise tại call của item 5


# ---------------------------------------------------------------------------
# Fakes — deterministic, đếm theo item
# ---------------------------------------------------------------------------


def _cls(**overrides) -> Classification:
    base = dict(
        categories=["nhãn-test"],
        ai_issue=None,
        sentiment="neutral",
        severity="medium",
        safety_issue=False,
        confidence=0.9,
        rationale="ok",
    )
    base.update(overrides)
    return Classification.model_validate(base)


#: Preset theo item: 2 & 7 confidence thấp → review; 4 & 9 critical → review;
#: còn lại sạch (conf 0.9 ≥ mọi ngưỡng) → không review.
PRESET_LOWCONF = _cls(confidence=0.5)
PRESET_CRITICAL = _cls(severity="critical")
PRESET_CLEAN = _cls()


def _preset_for(item_no: int) -> Classification:
    return {
        2: PRESET_LOWCONF,
        4: PRESET_CRITICAL,
        7: PRESET_LOWCONF,
        9: PRESET_CRITICAL,
    }.get(item_no, PRESET_CLEAN)


def _expected_review(item_no: int) -> bool:
    return item_no in {2, 4, 7, 9}


_ITEM_RE = re.compile(r"item (\d+)")


class FakeClassifier:
    """Thay `chat_structured` trong namespace `classifier`.

    Parse số item từ user message ("sanitized item N") để trả preset cố định
    theo item (không phụ thuộc thứ tự call — resume gọi lại vẫn đúng preset).
    Crash ĐÚNG MỘT LẦN ở `CRASH_ITEM`. Content lạ (không parse được số item —
    row của người khác trên DB dùng chung) vẫn được classify sạch nhưng bị
    GHI LẠI vào `touched_foreign` để test fail loudly kèm id.
    """

    def __init__(self):
        self.attempts_ok = 0
        self.attempts_total = 0
        self.success_items: set[int] = set()
        self.touched_foreign: list[uuid.UUID] = []
        self.crashed_once = False
        self.crash_enabled = True  # tắt cho test không cần crash

    def __call__(self, system, user, schema, **kwargs):  # chữ ký chat_structured
        self.attempts_total += 1
        fb_id = kwargs.get("feedback_id")
        m = _ITEM_RE.search(user or "")
        if m is None:
            self.touched_foreign.append(fb_id)
            return PRESET_CLEAN
        item_no = int(m.group(1))
        if self.crash_enabled and item_no == CRASH_ITEM and not self.crashed_once:
            self.crashed_once = True
            raise RuntimeError("simulated crash giữa batch (item 5)")
        self.attempts_ok += 1
        self.success_items.add(item_no)
        return _preset_for(item_no)


@pytest.fixture()
def fake_llm_embedder(monkeypatch):
    """Autouse-an-toàn-chi-phí: mọi test trong file chạy với LLM + embedder giả."""
    fake = FakeClassifier()
    monkeypatch.setattr(classifier_mod, "chat_structured", fake)

    embed_texts_seen: list[str] = []
    dim = get_settings().EMBEDDING_DIM

    def fake_embed_one(text: str) -> list[float]:
        embed_texts_seen.append(text)
        vec = [0.0] * dim
        vec[len(embed_texts_seen) % dim] = 1.0  # khác nhau nhẹ theo lượt gọi
        return vec

    monkeypatch.setattr(runner_mod, "embed_one", fake_embed_one)
    return {"classifier": fake, "embed_inputs": embed_texts_seen}


@pytest.fixture()
def batch(fake_llm_embedder):
    """Seed 10 feedbacks + cách ly row lạ + dọn sạch sau test.

    Quarantine: DB dev DÙNG CHUNG — nếu tồn tại feedback chưa claim KHÔNG phải
    của test, runner sẽ nhặt chúng. Fixture tạm gán chúng vào 1 run 'test-quarantine'
    rồi TRẢ NGUYÊN (analysis_run_id=NULL) khi teardown — không đụng labels.
    """
    state = {"run_ids": [], "qrun_id": None}
    with SessionLocal() as db:
        # dọn rác lần chạy trước (nếu teardown trước bị đứt)
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        db.commit()

        stray_ids = db.scalars(
            select(Feedback.id).where(Feedback.analysis_run_id.is_(None))
        ).all()

        qrun = AnalysisRun(
            pipeline_version="test-quarantine",
            llm_model="none",
            prompt_version="none",
            embedding_model="none",
            status=RunStatus.failed,
            total_count=len(stray_ids),
        )
        db.add(qrun)
        db.flush()
        state["qrun_id"] = qrun.id
        if stray_ids:
            db.execute(
                update(Feedback)
                .where(Feedback.id.in_(stray_ids))
                .values(analysis_run_id=qrun.id)
            )

        # Seed đúng thứ tự created_at tăng dần → runner xử lý item 1..10.
        base = datetime.now(timezone.utc) - timedelta(hours=1)
        ids: list[uuid.UUID] = []
        for i in range(1, N_ITEMS + 1):
            fb = Feedback(
                source=SOURCE,
                external_ref=f"{REF_PREFIX}{i:02d}",
                # đã sanitize sẵn — runner KHÔNG phải gọi presidio (nhẹ, nhanh)
                raw_content=f"Nội dung giả item {i} cho test runner (không PII)",
                sanitized_content=f"sanitized item {i}",
                created_at=base + timedelta(seconds=i),
            )
            db.add(fb)
            db.flush()
            ids.append(fb.id)
        db.commit()
    state["ids"] = ids

    yield state

    with SessionLocal() as db:
        if stray_ids:
            db.execute(
                update(Feedback)
                .where(Feedback.id.in_(stray_ids))
                .values(analysis_run_id=None)
            )
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        for rid in [*state["run_ids"], state["qrun_id"]]:
            run = db.get(AnalysisRun, rid)
            if run is not None:
                db.delete(run)
        db.commit()


def _make_run(batch, total: int) -> uuid.UUID:
    """Tạo row run trực tiếp (không qua API — tránh BackgroundTasks thật)."""
    with SessionLocal() as db:
        run = AnalysisRun(
            pipeline_version="v1",
            llm_model="fake-model",
            prompt_version="v1",
            embedding_model="fake-embed",
            total_count=total,
        )
        db.add(run)
        db.commit()
        batch["run_ids"].append(run.id)
        return run.id


# ---------------------------------------------------------------------------
# Kịch bản chính: crash → resume → mỗi item classify đúng MỘT LẦN
# ---------------------------------------------------------------------------


def test_crash_then_resume_classifies_each_item_exactly_once(batch, fake_llm_embedder):
    rid = _make_run(batch, N_ITEMS)

    # ---- Lượt 1: crash ở item 5 -------------------------------------------------
    run_analysis(rid)

    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert run.status is RunStatus.failed
        assert "RuntimeError" in (run.error or "")
        assert run.completed_at is not None
        assert run.processed_count == 4  # items 1–4 xong trước crash

        rows = {i: db.get(Feedback, batch["ids"][i - 1]) for i in range(1, N_ITEMS + 1)}
        for i in range(1, 5):
            assert rows[i].categories is not None, f"item {i} phải đã có labels"
            assert rows[i].embedding is not None
        for i in range(5, N_ITEMS + 1):
            assert rows[i].categories is None, f"item {i} chưa được xử lý"

    processed_mid = run.processed_count

    # ---- Lượt 2: RESUME CÙNG RUN ------------------------------------------------
    run_analysis(rid)

    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid)
        assert run.status is RunStatus.completed
        # resume heal trọn vẹn → error cũ từ lượt crash phải được XÓA (runner
        # chỉ giữ summary cho lỗi item-level của lượt hiện tại)
        assert run.error is None
        # monotonic: 4 → 10 và không vượt total
        assert processed_mid <= run.processed_count <= run.total_count
        assert run.processed_count == N_ITEMS

        rows = {i: db.get(Feedback, batch["ids"][i - 1]) for i in range(1, N_ITEMS + 1)}
        for i in range(1, N_ITEMS + 1):
            r = rows[i]
            assert r.categories == ["nhãn-test"]
            assert r.severity.value == _preset_for(i).severity.value
            assert r.confidence == pytest.approx(_preset_for(i).confidence)
            # công thức HITL khớp kỳ vọng per-item (plan §3.3)
            assert r.requires_human_review is _expected_review(i), f"item {i}"
            # Phase 13 Task 1: row đủ điều kiện HITL phải được đẩy sang 'pending'
            # (vào được hàng chờ review); row thường giữ 'unreviewed'.
            expected_rs = (
                ReviewStatus.pending if _expected_review(i) else ReviewStatus.unreviewed
            )
            assert r.review_status is expected_rs, f"review_status item {i}"
            # embedding lưu KÈM model + dim — store_embedding THẬT đọc tên model
            # từ settings (fake chỉ thay embed_one), đúng hợp đồng plan 08.
            assert r.embedding_model == get_settings().EMBEDDING_MODEL
            assert r.embedding_dim == get_settings().EMBEDDING_DIM
            assert len(r.embedding) == get_settings().EMBEDDING_DIM
            assert r.pii_detected is False  # sanitize không bị gọi lại

    # ---- Đếm call: mỗi item classify ĐÚNG MỘT LẦN (10, KHÔNG phải 14) ----------
    fake = fake_llm_embedder["classifier"]
    assert fake.crashed_once is True
    assert fake.success_items == set(range(1, N_ITEMS + 1))  # đủ 10 item, không thiếu
    assert fake.attempts_total == N_ITEMS + 1  # 10 success + đúng 1 attempt crash
    assert fake.attempts_ok == N_ITEMS  # ← assertion trung tâm idempotency
    assert fake.touched_foreign == [], "runner nhặt phải row lạ — kiểm tra quarantine"
    assert len(fake_llm_embedder["embed_inputs"]) == N_ITEMS


# ---------------------------------------------------------------------------
# Run không còn việc gì → completed ngay, không đụng LLM
# ---------------------------------------------------------------------------


def test_run_with_no_pending_items_completes_immediately(batch, fake_llm_embedder):
    # Lượt 1 (không crash): claim + xử lý trọn 10 item → DB không còn gì chưa xong.
    fake_llm_embedder["classifier"].crash_enabled = False
    rid1 = _make_run(batch, N_ITEMS)
    run_analysis(rid1)
    with SessionLocal() as db:
        assert db.get(AnalysisRun, rid1).status is RunStatus.completed

    # Lượt 2: run mới trên trạng thái "hết việc" → completed NGAY, 0 call LLM.
    before = fake_llm_embedder["classifier"].attempts_total
    embed_before = len(fake_llm_embedder["embed_inputs"])
    rid2 = _make_run(batch, 0)
    run_analysis(rid2)

    with SessionLocal() as db:
        run = db.get(AnalysisRun, rid2)
        assert run.status is RunStatus.completed
        assert run.processed_count == 0
        assert run.total_count == 0
        assert run.completed_at is not None
        assert run.error is None
    assert fake_llm_embedder["classifier"].attempts_total == before
    assert len(fake_llm_embedder["embed_inputs"]) == embed_before


# ---------------------------------------------------------------------------
# API endpoints — tạo run / progress / results (job nền bị patch để không chạy)
# ---------------------------------------------------------------------------


def _login_headers(client) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={"username": SEED_EMAILS[UserRole.pm], "password": TEST_PASSWORDS[UserRole.pm]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_runs_endpoints_create_progress_results(client, batch, monkeypatch):
    from app.api.routes import analysis as analysis_routes

    scheduled: list[uuid.UUID] = []
    monkeypatch.setattr(
        analysis_routes, "run_analysis", lambda rid: scheduled.append(rid)
    )

    headers = _login_headers(client)
    with SessionLocal() as db:
        # quarantine đảm bảo chỉ đúng 10 row seed của test là chưa claim
        count_unclaimed = len(
            db.scalars(
                select(Feedback.id).where(Feedback.analysis_run_id.is_(None))
            ).all()
        )
    assert count_unclaimed == N_ITEMS

    resp = client.post("/api/analysis/runs", headers=headers)
    assert resp.status_code == 201, resp.text
    rid = uuid.UUID(resp.json()["run_id"])
    batch["run_ids"].append(rid)
    assert scheduled == [rid]  # job nền được schedule đúng run vừa tạo

    poll = client.get(f"/api/analysis/runs/{rid}", headers=headers)
    assert poll.status_code == 200, poll.text
    body = poll.json()
    assert body["status"] == "running"
    assert body["processed_count"] == 0
    assert body["total_count"] == count_unclaimed
    assert body["error"] is None

    # Runner bị patch no-op → tự gắn seed rows vào run như runner thật sẽ làm,
    # rồi kiểm tra results trả ĐỦ items thuộc run kèm labels chưa xử lý.
    with SessionLocal() as db:
        db.execute(
            update(Feedback)
            .where(Feedback.external_ref.like(f"{REF_PREFIX}%"))
            .values(analysis_run_id=rid)
        )
        db.commit()

    results = client.get(f"/api/analysis/runs/{rid}/results?limit=100", headers=headers)
    assert results.status_code == 200, results.text
    payload = results.json()
    assert payload["total"] == N_ITEMS
    got_ids = {item["id"] for item in payload["items"]}
    assert {str(fid) for fid in batch["ids"]} <= got_ids
    for item in payload["items"]:
        if item["id"] in {str(fid) for fid in batch["ids"]}:
            assert item["categories"] is None  # chưa ai phân loại

    assert client.get(f"/api/analysis/runs/{uuid.uuid4()}", headers=headers).status_code == 404
    # anon → 401 (guard router-level). LƯU Ý: client giữ cookie từ lúc login
    # ở trên — phải clear trước, nếu không request vẫn mang token PM.
    client.cookies.clear()
    assert client.post("/api/analysis/runs").status_code == 401
