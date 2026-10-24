"""Exercise bounded scheduling with real threads, no providers or database."""

from importlib import import_module
from contextvars import ContextVar
from threading import Barrier, Event, Lock, get_ident


def test_items_overlap_but_persistence_stays_on_coordinator():
    process_items = import_module("app.jobs.analysis_workers").process_items
    coordinator = get_ident()
    barrier, lock = Barrier(3), Lock()
    state = {"active": 0, "peak": 0}
    saved = []

    def process(item):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        barrier.wait(timeout=3)
        with lock:
            state["active"] -= 1
        return item * 10

    def save(item, result):
        assert get_ident() == coordinator
        saved.append((item, result))

    process_items(range(6), process, save, lambda: False, max_workers=3)
    assert state["peak"] == 3
    assert sorted(saved) == [(0, 0), (1, 10), (2, 20), (3, 30), (4, 40), (5, 50)]


def test_stop_drains_started_items_without_submitting_more():
    process_items = import_module("app.jobs.analysis_workers").process_items
    stopped, first_saved = Event(), Event()
    saved = []

    def process(item):
        if item == 1:
            assert first_saved.wait(timeout=3)
        return item

    def save(item, result):
        saved.append(result)
        stopped.set()
        first_saved.set()

    process_items(range(10), process, save, stopped.is_set, max_workers=2)
    assert sorted(saved) == [0, 1]


def test_already_stopped_does_not_consume_items():
    process_items = import_module("app.jobs.analysis_workers").process_items

    def items():
        raise AssertionError("cancelled run must not consume pending items")
        yield

    process_items(items(), lambda item: item, lambda *args: None, lambda: True, max_workers=3)


def test_workers_preserve_callers_trace_context():
    process_items = import_module("app.jobs.analysis_workers").process_items
    trace = ContextVar("synthetic_trace", default=None)
    token = trace.set("synthetic-run")
    saved = []
    try:
        process_items([1, 2], lambda item: trace.get(),
            lambda item, result: saved.append(result), lambda: False, max_workers=2)
    finally:
        trace.reset(token)
    assert saved == ["synthetic-run", "synthetic-run"]
