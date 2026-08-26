"""Integration tests Phase 18 Task 2 — tools `classify_batch` / `embed_batch`.

⚠️ Marker `integration` — DB Supabase thật cho feedbacks; LLM/embeddings MOCK
hoàn toàn (autouse fixture) nên không phát sinh chi phí dù DB dùng chung.

Kiểm chứng theo plan §3 Task 2:
- Passthrough `feedback_id`/`analysis_run_id` từ tool xuống classifier (kwargs
  của chat_structured — vào llm_call_logs);
- Item lỗi (LLMStructureError / EmbeddingDimError) KHÔNG chặn item kế;
- Row đã có labels / đã có embedding trong danh sách chọn → `skipped_ids`
  (không tốn call);
- Output shape `{processed, failed, skipped_ids}` đúng hợp đồng registry.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import ReviewStatus, RunStatus
from app.models.feedback import Feedback
from app.models.llm_call_log import LlmCallLog
from app.schemas.taxonomy import Classification
from app.services import classifier as classifier_mod
from app.services.embedder import EmbeddingDimError
from app.services.llm_client import LLMStructureError
from happynest_agent.tools import classify_batch as cb_mod
from happynest_agent.tools import embed_batch as eb_mod

pytestmark = pytest.mark.integration

SOURCE = "test-agtool"
REF_PREFIX = "agtool-"
N_ITEMS = 6
FAIL_ITEM = 3  # item lỗi giả lập (1-indexed)

_ITEM_RE = re.compile(r"item (\d+)")


def _cls(**overrides) -> Classification:
    base = dict(
        categories=["nhãn-tool"],
        ai_issue=None,
        sentiment="neutral",
        severity="medium",
        safety_issue=False,
        confidence=0.9,
        rationale="ok",
    )
    base.update(overrides)
    return Classification.model_validate(base)


class FakeChatStructured:
    """Thay `chat_structured` trong namespace `classifier` — record passthrough."""

    def __init__(self):
        self.calls: list[dict] = []  # kwargs mỗi lần gọi thành công/thất bại
        self.ok_items: set[int] = set()

    def __call__(self, system, user, schema, **kwargs):
        self.calls.append(kwargs)
        m = _ITEM_RE.search(user or "")
        if m and int(m.group(1)) == FAIL_ITEM:
            raise LLMStructureError(f"simulated parse fail (item {FAIL_ITEM})")
        if m is not None:
            self.ok_items.add(int(m.group(1)))
        return _cls()


class FakeEmbedOne:
    def __init__(self):
        self.seen: list[str] = []
        self.n = 0

    def __call__(self, text: str) -> list[float]:
        if f"item {FAIL_ITEM:02d}" in text or f"item {FAIL_ITEM} " in text:
            raise EmbeddingDimError(f"simulated dim reject (item {FAIL_ITEM})")
        self.seen.append(text)
        self.n += 1
        dim = get_settings().EMBEDDING_DIM
        vec = [0.0] * dim
        vec[self.n % dim] = 1.0
        return vec


@pytest.fixture()
def fakes(monkeypatch):
    chat = FakeChatStructured()
    emb = FakeEmbedOne()
    # Patch tại namespace TOOL (tool import hàm trực tiếp) — classify_feedback
    # THẬT vẫn chạy để passthrough kwargs đi trọn đường vào chat_structured;
    # store_embedding THẬT vẫn chạy để assert đủ triplet model/dim.
    monkeypatch.setattr(classifier_mod, "chat_structured", chat)
    monkeypatch.setattr(eb_mod, "embed_one", emb)
    return {"chat": chat, "embed": emb}


def _quarantine_strays(db) -> uuid.UUID | None:
    """Gán tạm mọi row chưa claim (KHÔNG phải của test) vào 1 run 'failed'
    để tool không nhặt phải — trả nguyên `analysis_run_id=NULL` khi teardown.
    (Cùng kỹ thuật quarantine của test_classifier_idempotency.)"""
    stray_ids = db.scalars(
        select(Feedback.id).where(Feedback.analysis_run_id.is_(None))
    ).all()
    if not stray_ids:
        return None
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
    db.execute(
        update(Feedback)
        .where(Feedback.id.in_(stray_ids))
        .values(analysis_run_id=qrun.id)
    )
    return qrun.id


@pytest.fixture()
def seeded(request):
    """Seed 6 feedbacks + quarantine row lạ trên DB dùng chung; dọn sạch sau.

    GUARD chống nhiễm chéo (bài học 2026-08-26): DB dev dùng chung — nếu ngoài
    6 row seed Còn tồn tại row nào khác khớp predicate của tool (runner thật
    đang chạy, hay pool có row mồ côi), test phải SKIP thay vì để tool xử lý
    row người khác. Không bao giờ nuốt pool của runner khác làm điều kiện tiên quyết.
    """
    state: dict = {"run_ids": [], "qrun_id": None}
    with SessionLocal() as db:
        # rác lần chạy trước (teardown từng bị rollback): logs TRƯỚC rồi mới
        # feedbacks — llm_call_logs.feedback_id FK restrict.
        old_ids = db.scalars(
            select(Feedback.id).where(Feedback.external_ref.like(f"{REF_PREFIX}%"))
        ).all()
        if old_ids:
            db.query(LlmCallLog).filter(
                LlmCallLog.feedback_id.in_(old_ids)
            ).delete(synchronize_session=False)
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        db.commit()

        state["qrun_id"] = _quarantine_strays(db)

        base = datetime.now(timezone.utc) - timedelta(hours=1)
        ids: list[uuid.UUID] = []
        for i in range(1, N_ITEMS + 1):
            fb = Feedback(
                source=SOURCE,
                external_ref=f"{REF_PREFIX}{i:02d}",
                # sanitize sẵn — tool không phải gọi presidio (nhanh, rẻ)
                raw_content=f"Nội dung giả item {i} (không PII)",
                sanitized_content=f"sanitized item {i:02d} ",
                created_at=base + timedelta(seconds=i),
            )
            db.add(fb)
            db.flush()
            ids.append(fb.id)

        run = AnalysisRun(
            pipeline_version="v1",
            llm_model="fake-model",
            prompt_version="v1",
            embedding_model="fake-embed",
            total_count=N_ITEMS,
        )
        db.add(run)
        db.commit()
        state.update(ids=ids, run_id=run.id)

        # GUARD: predicate của tool giờ phải khớp ĐÚNG 6 row seed.
        from sqlalchemy import or_

        others = len(
            db.scalars(
                select(Feedback.id).where(
                    or_(
                        Feedback.analysis_run_id.is_(None),
                        Feedback.categories.is_(None),
                    ),
                    Feedback.external_ref.notlike(f"{REF_PREFIX}%"),
                ).limit(N_ITEMS + 1)
            ).all()
        )
        if others > 0:
            pytest.skip(
                f"DB dùng chung còn {others}+ row ngoài dự kiến khớp predicate "
                "(runner thật đang chạy?) — bỏ qua để không nhiễm chéo."
            )
    yield state

    with SessionLocal() as db:
        if state.get("qrun_id") and db.get(AnalysisRun, state["qrun_id"]) is not None:
            db.execute(
                update(Feedback)
                .where(Feedback.analysis_run_id == state["qrun_id"])
                .values(analysis_run_id=None)
            )
        all_run_ids = [
            rid
            for rid in [*state.get("run_ids", []), state.get("run_id"), state.get("qrun_id")]
            if rid
        ]
        # dọn llm_call_logs TRƯỚC (FK restrict về analysis_runs/feedbacks)
        for rid in all_run_ids:
            db.query(LlmCallLog).filter(LlmCallLog.analysis_run_id == rid).delete(
                synchronize_session=False
            )
        db.query(LlmCallLog).filter(
            LlmCallLog.feedback_id.in_(state.get("ids", []))
        ).delete(synchronize_session=False)
        db.query(Feedback).filter(
            Feedback.external_ref.like(f"{REF_PREFIX}%")
        ).delete(synchronize_session=False)
        for rid in all_run_ids:
            run = db.get(AnalysisRun, rid)
            if run is not None:
                db.delete(run)
        db.commit()


# ---------------------------------------------------------------------------
# classify_batch
# ---------------------------------------------------------------------------


def test_classify_batch_passthrough_and_labels(seeded, fakes):
    with SessionLocal() as db:
        out = cb_mod.execute(db, cb_mod.ClassifyBatchIn(run_id=seeded["run_id"]))

    assert (out.processed, out.failed, out.skipped_ids) == (N_ITEMS, 0, [])
    chat = fakes["chat"]
    # passthrough: MỖI call mang đúng feedback_id + analysis_run_id của run
    called_ids = {c["feedback_id"] for c in chat.calls}
    assert called_ids == set(seeded["ids"])
    assert {c["analysis_run_id"] for c in chat.calls} == {seeded["run_id"]}
    with SessionLocal() as db:
        for i in range(1, N_ITEMS + 1):
            fb = db.get(Feedback, seeded["ids"][i - 1])
            assert fb.categories == ["nhãn-tool"]
            assert fb.confidence == pytest.approx(0.9)
            # công thức HITL: preset sạch → không review, status unreviewed
            assert fb.requires_human_review is False
            assert fb.review_status is ReviewStatus.unreviewed


def test_classify_batch_error_does_not_block_next(seeded, fakes):
    with SessionLocal() as db:
        out = cb_mod.execute(db, cb_mod.ClassifyBatchIn(run_id=seeded["run_id"]))

    assert out.failed == 1  # đúng item lỗi fail, không lan
    assert out.processed == N_ITEMS - 1
    with SessionLocal() as db:
        bad = db.get(Feedback, seeded["ids"][FAIL_ITEM - 1])
        assert bad.categories is None, "item lỗi không được gán labels"
        for i in range(1, N_ITEMS + 1):
            if i == FAIL_ITEM:
                continue
            fb = db.get(Feedback, seeded["ids"][i - 1])
            assert fb.categories is not None, f"item {i} bị chặn sai"
    assert FAIL_ITEM not in fakes["chat"].ok_items


def test_classify_batch_skips_rows_with_labels(seeded, fakes):
    with SessionLocal() as db:
        cb_mod.execute(db, cb_mod.ClassifyBatchIn(run_id=seeded["run_id"]))
    before = len(fakes["chat"].calls)

    with SessionLocal() as db:
        out2 = cb_mod.execute(db, cb_mod.ClassifyBatchIn(run_id=seeded["run_id"]))

    # lượt 2: predicate vẫn NHẬT đủ 6 row (chưa ai claim) nhưng tất cả đã có
    # labels → skipped, KHÔNG một call LLM nào phát sinh thêm
    assert (out2.processed, out2.failed) == (0, 0)
    assert sorted(out2.skipped_ids) == sorted(seeded["ids"])
    assert len(fakes["chat"].calls) == before


# ---------------------------------------------------------------------------
# embed_batch
# ---------------------------------------------------------------------------


def test_embed_batch_triplet_and_skip_existing(seeded, fakes):
    with SessionLocal() as db:
        out = eb_mod.execute(db, eb_mod.EmbedBatchIn(run_id=seeded["run_id"]))

    assert (out.processed, out.failed, out.skipped_ids) == (N_ITEMS, 0, [])
    s = get_settings()
    with SessionLocal() as db:
        for i in range(1, N_ITEMS + 1):
            fb = db.get(Feedback, seeded["ids"][i - 1])
            assert fb.embedding is not None and len(fb.embedding) == s.EMBEDDING_DIM
            assert fb.embedding_model == s.EMBEDDING_MODEL
            assert fb.embedding_dim == s.EMBEDDING_DIM
    # embed tính TỪ sanitized_content (PII boundary)
    assert all(t.startswith("sanitized item") for t in fakes["embed"].seen)

    with SessionLocal() as db:
        out2 = eb_mod.execute(db, eb_mod.EmbedBatchIn(run_id=seeded["run_id"]))
    assert (out2.processed, out2.failed) == (0, 0)
    assert sorted(out2.skipped_ids) == sorted(seeded["ids"])
    assert len(fakes["embed"].seen) == N_ITEMS  # không embed lại


def test_embed_batch_error_does_not_block_next(seeded, fakes):
    with SessionLocal() as db:
        out = eb_mod.execute(db, eb_mod.EmbedBatchIn(run_id=seeded["run_id"]))

    assert (out.processed, out.failed) == (N_ITEMS - 1, 1)
    with SessionLocal() as db:
        bad = db.get(Feedback, seeded["ids"][FAIL_ITEM - 1])
        assert bad.embedding is None
        for i in range(1, N_ITEMS + 1):
            if i == FAIL_ITEM:
                continue
            assert db.get(Feedback, seeded["ids"][i - 1]).embedding is not None
