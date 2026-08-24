"""Stub endpoints cho các giai đoạn sau execute-plan §7.

Mỗi endpoint trả 501 kèm docstring giải thích phase nào làm gì.
DoD Phase 12 sẽ rà lại các stub này còn nguyên (không bị triển khai sớm).
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["admin-stubs"])


def _not_implemented(endpoint: str, note: str) -> HTTPException:
    return HTTPException(status_code=501, detail=f"{endpoint} chưa triển khai. {note}")


@router.get("/clusters")
def list_clusters():
    """STUB 501 — clustering + trend/emerging/spike detection thuộc giai đoạn sau
    Backend Foundation (ngoài scope phase hiện tại). Bảng `clusters` đã có sẵn."""
    raise _not_implemented("GET /api/clusters", "Cần clustering engine (giai đoạn sau).")


@router.get("/insights")
def list_insights():
    """STUB 501 — insight generation evidence-backed thuộc giai đoạn sau.
    Bảng `insights` đã có sẵn."""
    raise _not_implemented("GET /api/insights", "Cần insight engine (giai đoạn sau).")


@router.post("/reviews/{feedback_id}")
def submit_review(feedback_id: str):
    """STUB 501 — HITL review flow (LangGraph interrupt) là giai đoạn sau.
    Bảng `human_reviews` đã có sẵn; trigger rule `requires_human_review` đã
    compute ở cột feedbacks từ Phase 05/07."""
    raise _not_implemented("POST /api/reviews/{feedback_id}", "Cần HITL graph.")


@router.post("/corrections/{feedback_id}")
def submit_correction(feedback_id: str):
    """STUB 501 — correction→few-shot loop là giai đoạn sau.
    Bảng `correction_examples` đã có sẵn."""
    raise _not_implemented("POST /api/corrections/{feedback_id}", "Cần correction loop.")


@router.get("/reports/summary")
def reports_summary():
    """STUB 501 — báo cáo tổng hợp cho PM là giai đoạn sau."""
    raise _not_implemented("GET /api/reports/summary", "Cần reports layer.")
