"""QA HN-013 (2026-11-11): chạy lượt phân loại kế tiếp trả 422 không đọc được.

Nguyên nhân: `analysis_state=pending` gồm cả mục ĐANG nằm trong một run. Vault
dùng nó để chọn file chạy tiếp ở phạm vi "All imports" nên chọn nhầm file đang
chạy → preview 0 mục → `confirmed_item_count=0` vi phạm `ge=1` → 422.

Hợp đồng sau khi sửa:
- `analysis_state=eligible` = chờ phân loại VÀ chưa bị run nào claim;
- tạo run trên file không còn mục chạy được → 409 `nothing_eligible` kèm
  message đọc được, không tạo run rỗng.

Marker `integration` — DB thật, không gọi LLM (request bị chặn trước khi job
nền được xếp hàng).
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import ImportStatus, RunStatus
from app.models.feedback import Feedback
from app.models.import_ import Import
from tests.conftest import SEED_EMAILS, TEST_PASSWORDS

pytestmark = pytest.mark.integration

SOURCE = "test-run-eligibility"


def _login(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/token",
        data={
            "username": SEED_EMAILS["primary"],
            "password": TEST_PASSWORDS["primary"],
        },
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def claimed_env(test_product):
    """Một file có 1 mục đang bị run claim + 1 mục đã phân loại xong."""
    ids: dict[str, uuid.UUID] = {}

    def _clean():
        with SessionLocal() as db:
            db.execute(delete(Feedback).where(Feedback.source == SOURCE))
            if "run" in ids:
                db.execute(delete(AnalysisRun).where(AnalysisRun.id == ids["run"]))
            if "import" in ids:
                db.execute(delete(Import).where(Import.id == ids["import"]))
            db.commit()

    with SessionLocal() as db:
        db.execute(delete(Feedback).where(Feedback.source == SOURCE))
        import_row = Import(
            product_id=test_product.id,
            source_type="csv",
            original_filename="eligibility.csv",
            status=ImportStatus.imported,
            row_count=2,
        )
        db.add(import_row)
        db.flush()
        run = AnalysisRun(
            pipeline_version="test",
            llm_model="test",
            prompt_version="test",
            embedding_model="test",
            import_id=import_row.id,
            product_id=test_product.id,
            mode="batch",
            total_count=1,
            status=RunStatus.running,
        )
        db.add(run)
        db.flush()
        now = datetime.now(UTC)
        # ⚠️ mục chờ = KHÔNG gửi key ai_analysis (SQL NULL), xem
        # test_feedback_list_filters._seed.
        db.add(
            Feedback(
                product_id=test_product.id,
                import_id=import_row.id,
                analysis_run_id=run.id,
                source=SOURCE,
                source_record_id="claimed",
                occurred_at=now,
                raw_content="noi dung gia claimed (khong PII)",
                feedback_text="noi dung gia claimed",
            )
        )
        db.add(
            Feedback(
                product_id=test_product.id,
                import_id=import_row.id,
                source=SOURCE,
                source_record_id="done",
                occurred_at=now,
                raw_content="noi dung gia done (khong PII)",
                feedback_text="noi dung gia done",
                ai_analysis={"topics": ["x"], "uncategorized": False},
            )
        )
        db.commit()
        ids["import"], ids["run"] = import_row.id, run.id

    yield {"product_id": test_product.id, **ids}
    _clean()


def _refs(client: TestClient, auth: dict, env: dict, state: str) -> list[str]:
    resp = client.get(
        f"/api/feedbacks?limit=50&import_id={env['import']}&analysis_state={state}",
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    return [item["source_record_id"] for item in resp.json()["items"]]


def test_eligible_excludes_rows_claimed_by_a_running_run(
    claimed_env, client: TestClient
) -> None:
    auth = _login(client)
    # `pending` vẫn tính mục đang chạy (vault hiển thị "chờ phân loại")…
    assert _refs(client, auth, claimed_env, "pending") == ["claimed"]
    # …nhưng không mục nào còn chạy được cho tới khi run kia trả claim.
    assert _refs(client, auth, claimed_env, "eligible") == []


def test_preview_reports_zero_when_everything_is_claimed(
    claimed_env, client: TestClient
) -> None:
    auth = _login(client)
    resp = client.post(
        "/api/analysis/runs/preview",
        json={"mode": "batch", "import_id": str(claimed_env["import"])},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["selected_count"] == 0
    assert resp.json()["eligible_count"] == 0


def test_create_run_with_nothing_eligible_is_a_readable_409(
    claimed_env, client: TestClient
) -> None:
    """Trước khi sửa: 422 `Input should be greater than or equal to 1`."""
    auth = _login(client)
    resp = client.post(
        "/api/analysis/runs",
        json={
            "mode": "batch",
            "import_id": str(claimed_env["import"]),
            "confirmed_item_count": 0,
        },
        headers=auth,
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "nothing_eligible"
    assert "lượt khác" in detail["message"]

    # Không tạo run rỗng, không đụng claim của run đang chạy.
    with SessionLocal() as db:
        runs = db.scalar(
            select(func.count())
            .select_from(AnalysisRun)
            .where(AnalysisRun.import_id == claimed_env["import"])
        )
        claimed = db.scalar(
            select(Feedback.analysis_run_id).where(
                Feedback.source == SOURCE, Feedback.source_record_id == "claimed"
            )
        )
    assert runs == 1
    assert claimed == claimed_env["run"]
