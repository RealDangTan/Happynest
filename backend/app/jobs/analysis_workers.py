"""Bounded provider I/O; only the caller thread persists results."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextvars import copy_context


def process_items(items, process, save, should_stop, *, max_workers: int) -> None:
    """Stop submitting on cancellation/failure, but persist already-started work.

    There is no unbounded executor queue: at most max_workers items can consume
    provider budget at once. `items`, `save` and `should_stop` stay on the caller.
    """
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    pending = iter(items)
    exhausted = False
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="listen") as pool:
        inflight = {}
        while True:
            stop = should_stop()
            while not stop and not exhausted and len(inflight) < max_workers:
                try:
                    item = next(pending)
                except StopIteration:
                    exhausted = True
                    break
                inflight[pool.submit(copy_context().run, process, item)] = item
            if not inflight:
                return
            completed, _ = wait(inflight, return_when=FIRST_COMPLETED)
            for future in completed:
                save(inflight.pop(future), future.result())
