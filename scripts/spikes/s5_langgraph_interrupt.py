"""Spike S5 — LangGraph interrupt -> process CHẾT -> resume với AsyncPostgresSaver?

Nền tảng HITL review cho phase sau (production graph vẫn ngoài scope giai đoạn này).
Câu hỏi: checkpoint lưu Supabase có cho resume đúng sau khi process thoát hẳn,
KHÔNG nhân đôi side effect?

Kịch bản (2 tiến trình Python riêng biệt, state chỉ nằm trên Postgres):
- `--phase start`: reset bảng side-effect `_spike_side_effects`, chạy graph
  A -> [interrupt trước B] -> C tới chỗ dừng, xác nhận B chưa thực thi
  (count == 0), THOÁT PROCESS.
- `--phase resume`: tiến trình MỚI nối lại thread cũ bằng ainvoke(None):
  B chạy đúng MỘT lần -> C xong -> assert count == 1.
  Pass -> tự dọn `_spike_side_effects` + 4 bảng checkpoint langgraph.

Checkpointer: AsyncPostgresSaver.from_conn_string(DATABASE_URL) nối thẳng Supabase;
setup() tạo 4 bảng checkpoint (env.py Phase 03 đã include_object loại đúng các
tên này khỏi Alembic — script đối chiếu và in bằng chứng).

Không LLM tokens. Output JSON ra stdout + results/ (gitignored).
Chạy:
    uv run python ../scripts/spikes/s5_langgraph_interrupt.py --phase start
    uv run python ../scripts/spikes/s5_langgraph_interrupt.py --phase resume
"""

import argparse
import asyncio
import json
import selectors
import sys
import time
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import db_params, load_env_file, save_result, utf8_stdio  # noqa: E402

utf8_stdio()

import psycopg  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402

FX_TABLE = "public._spike_side_effects"
THREAD_ID = "spike-s5-interrupt-1"
# Đối chiếu với LANGGRAPH_CHECKPOINT_TABLES trong backend/alembic/env.py
ALEMBIC_FILTER_TABLES = {
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
}


def conn_string(env) -> str:
    """psycopg URI với userinfo percent-encoded (password chứa @ — RFC 3986)."""
    p = db_params(env)
    return (
        f"postgresql://{quote(p['user'])}:{quote(p['password'])}"
        f"@{p['host']}:{p['port']}/{p['dbname']}"
    )


# ---------------------------------------------------------------------------
# Side-effect counter: bảng riêng, đếm xuyên suốt 2 process qua DB
# ---------------------------------------------------------------------------

def fx_connect(env) -> psycopg.Connection:
    return psycopg.connect(**db_params(env), connect_timeout=20)


def fx_reset(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {FX_TABLE}")
        cur.execute(
            f"CREATE TABLE {FX_TABLE} "
            "(id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now())"
        )
    conn.commit()


def fx_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {FX_TABLE}")
        return int(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Graph tối giản: A -> B(side effect) -> C, dừng TRƯỚC B
# ---------------------------------------------------------------------------

class State(TypedDict):
    steps: list[str]


def build_graph(checkpointer, fx_conn):
    def node_a(state: State) -> dict:
        return {"steps": [*state["steps"], "a"]}

    def node_b(state: State) -> dict:
        # SIDE EFFECT duy nhất của graph: 1 INSERT mỗi lần node thực thi.
        with fx_conn.cursor() as cur:
            cur.execute(f"INSERT INTO {FX_TABLE} (ts) VALUES (now())")
        fx_conn.commit()
        return {"steps": [*state["steps"], "b"]}

    def node_c(state: State) -> dict:
        return {"steps": [*state["steps"], "c"]}

    builder = StateGraph(State)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.add_node("c", node_c)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", "c")
    builder.add_edge("c", END)
    return builder.compile(checkpointer=checkpointer, interrupt_before=["b"])


async def _list_checkpoint_tables(cs: str) -> list[str]:
    """Bảng checkpoint% thực tế trong public sau setup() — bằng chứng 'xuất hiện'."""
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(cs) as saver:
        await saver.setup()
        # from_conn_string cho saver.conn là AsyncConnection (không phải pool),
        # row_factory = dict_row do langgraph đặt sẵn.
        async with saver.conn.cursor() as cur:
            await cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE 'checkpoint%' "
                "ORDER BY table_name"
            )
            rows = await cur.fetchall()
            return [
                r["table_name"] if isinstance(r, dict) else r[0] for r in rows
            ]


async def run_phase(phase: str) -> dict:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    env = load_env_file()
    cs = conn_string(env)
    report: dict = {"spike": "S5", "phase": phase, "thread_id": THREAD_ID}

    t0 = time.perf_counter()
    checkpoint_tables = await _list_checkpoint_tables(cs)
    report["checkpoint_tables_after_setup"] = sorted(checkpoint_tables)
    report["alembic_filter_matches_reality"] = set(checkpoint_tables) == ALEMBIC_FILTER_TABLES

    async with AsyncPostgresSaver.from_conn_string(cs) as saver:
        await saver.setup()  # idempotent — migrations đã track từ phase trước
        fx = fx_connect(env)
        try:
            graph = build_graph(saver, fx)
            config = {"configurable": {"thread_id": THREAD_ID}}

            if phase == "start":
                fx_reset(fx)
                result = await graph.ainvoke({"steps": []}, config)
                snap = await graph.aget_state(config)
                report.update(
                    {
                        "result_at_interrupt": result,
                        "next_nodes": list(snap.next),
                        "side_effects_so_far": fx_count(fx),
                    }
                )
                report["stopped_before_b"] = report["next_nodes"] == ["b"]
                report["side_effect_not_yet_run"] = report["side_effects_so_far"] == 0
                report["pass"] = bool(report["stopped_before_b"] and report["side_effect_not_yet_run"])
                report["note"] = "process sẽ thoát — chạy lại với --phase resume như tiến trình MỚI"
            else:  # resume
                before = fx_count(fx)
                result = await graph.ainvoke(None, config)  # resume từ checkpoint
                elapsed = round(time.perf_counter() - t0, 2)
                snap = await graph.aget_state(config)
                after = fx_count(fx)
                report.update(
                    {
                        "side_effects_before_resume": before,
                        "result_after_resume": result,
                        "next_nodes_final": list(snap.next),
                        "side_effects_after_resume": after,
                        "resume_seconds": elapsed,
                    }
                )
                report["resumed_to_completion"] = (
                    report["next_nodes_final"] == [] and result.get("steps") == ["a", "b", "c"]
                )
                report["no_duplicate_side_effect"] = before == 0 and after == 1
                report["pass"] = bool(
                    report["resumed_to_completion"] and report["no_duplicate_side_effect"]
                )
        finally:
            fx.close()

    if phase == "resume":
        if report["pass"]:
            dropped = await _cleanup(env)
            report["cleanup_dropped"] = sorted(dropped)
        else:
            report["cleanup_dropped"] = []
            report["note"] = (
                "FAIL — GIỮ nguyên bảng side-effect + checkpoint để debug; dọp tay khi xong."
            )

    return report


async def _cleanup(env) -> list[str]:
    """Dọn đồ toy sau PASS: bảng side-effect + 4 bảng checkpoint langgraph."""
    names = [*ALEMBIC_FILTER_TABLES, FX_TABLE.split(".")[-1]]
    conn = fx_connect(env)
    dropped = []
    try:
        with conn.cursor() as cur:
            for name in names:
                cur.execute(f'DROP TABLE IF EXISTS public."{name}" CASCADE')
                dropped.append(name)
        conn.commit()
    finally:
        conn.close()
    return dropped


def main() -> None:
    parser = argparse.ArgumentParser(description="Spike S5 langgraph interrupt/resume")
    parser.add_argument("--phase", choices=["start", "resume"], required=True)
    args = parser.parse_args()

    # Windows mặc định ProactorEventLoop — psycopg async chỉ chạy trên selector loop.
    report = asyncio.run(
        run_phase(args.phase),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
    save_result(f"s5_langgraph_{args.phase}", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report.get("pass") else 1)


if __name__ == "__main__":
    main()
