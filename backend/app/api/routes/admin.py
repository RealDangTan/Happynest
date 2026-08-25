"""Stub endpoints cho các giai đoạn sau execute-plan §7.

Mỗi endpoint trả 501 kèm docstring giải thích phase nào làm gì.
Lịch sử: Phase 13 đã thay 2 stub reviews/corrections bằng routes thật
(routes/review.py); file này còn 3 stub clusters/insights/reports cho
P3/P4 (plans 14–16).
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


@router.get("/reports/summary")
def reports_summary():
    """STUB 501 — báo cáo tổng hợp cho PM là giai đoạn sau."""
    raise _not_implemented("GET /api/reports/summary", "Cần reports layer.")
