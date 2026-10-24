"""Nonblocking review delivery. A receipt is not an approval confirmation.

The checkpoint and insight review tables remain authoritative. In-flight state
is process-local: restart exposes the original gate or the committed outcome.
"""
import logging
import threading
from time import monotonic
from uuid import UUID

from understand_agent import runner

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_states: dict[UUID, dict] = {}


def start_worker(fn, *args) -> None:
    # A separate thread owns all continuation I/O. Do not attach long graph
    # work to the HTTP response lifecycle (proxy clients may buffer it).
    threading.Thread(target=fn, args=args, name=f"review-{args[0]}", daemon=True).start()


def review_state(run_id: UUID) -> dict:
    with _lock:
        value = _states.get(run_id)
        if value and (value["processing"] or value["expires"] > monotonic()):
            return dict(value)
        _states.pop(run_id, None)
    return {"processing": False, "error": None}


def queue_review(run_id: UUID, payload: dict, enqueue) -> None:
    with _lock:
        if _states.get(run_id, {}).get("processing"):
            raise ValueError("Quyết định đang được xử lý. Vui lòng đợi kết quả.")
        _states[run_id] = {"processing": True, "action": payload.get("action"), "error": None, "expires": monotonic() + 600}
    try:
        if not runner.get_run_snapshot(run_id):
            raise ValueError("Phiên không còn chờ duyệt. Hãy cập nhật trạng thái.")
        enqueue(_resume, run_id, dict(payload))
    except Exception:
        with _lock:
            _states.pop(run_id, None)
        raise


def _resume(run_id: UUID, payload: dict) -> None:
    error = None
    runner.invalidate_snapshot(run_id)
    try:
        runner.resume_with_decision(run_id, payload)
    except Exception:
        logger.exception("review continuation failed run=%s", run_id)
        error = "Chưa xác nhận được quyết định. Hãy kiểm tra lại trạng thái trước khi thử lại."
    finally:
        runner.invalidate_snapshot(run_id)
        with _lock:
            # Bound memory without evicting active work.
            now = monotonic()
            for key in list(_states):
                if not _states[key]["processing"] and _states[key]["expires"] <= now:
                    _states.pop(key, None)
            _states[run_id] = {"processing": False, "error": error, "expires": now + 600}
