"""Interactive owner terminal for the production UNDERSTAND/ACT agent.

The terminal is intentionally a thin presentation layer over the existing
LangGraph runner. Raw questions are sanitized before the graph sees them and
live trace output is metadata-only: no prompt/response payload is rendered.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol


OutputFn = Callable[[str], None]
InputFn = Callable[[str], str]


@dataclass(frozen=True)
class TerminalRun:
    run_id: str
    insight_id: str
    title: str
    finding: str
    confidence: float
    evidence_count: int


@dataclass(frozen=True)
class ActionSummary:
    created: int
    skipped: list[str]
    top_actions: list[tuple[str, float, str]]


class TerminalRuntime(Protocol):
    def tracing_status(self) -> str: ...

    def list_products(self) -> list[tuple[str, str]]: ...

    def sanitize_question(self, raw: str) -> str: ...

    def run_understand(
        self, product_id: str, question: str, output: OutputFn
    ) -> TerminalRun: ...

    def decide(self, run_id: str, action: str) -> str: ...

    def generate_actions(self, insight_id: str, output: OutputFn) -> ActionSummary: ...

    def flush(self) -> None: ...


def format_trace_row(row) -> str:
    """Render trace metadata without ever touching input/output payload fields."""
    call_type = getattr(row.call_type, "value", str(row.call_type))
    status = "ERROR" if row.error else "OK"
    prompt_tokens = row.prompt_tokens if row.prompt_tokens is not None else "?"
    completion_tokens = (
        row.completion_tokens if row.completion_tokens is not None else "?"
    )
    return (
        f"[trace] {call_type} | {status} | {row.latency_ms}ms | "
        f"tokens {prompt_tokens}→{completion_tokens} | {row.model}"
    )


def _choose_product(
    products: list[tuple[str, str]], input_fn: InputFn, output_fn: OutputFn
) -> tuple[str, str]:
    if not products:
        raise RuntimeError("Chưa có product trong database.")
    output_fn("Products:")
    for index, (_, name) in enumerate(products, start=1):
        output_fn(f"  {index}. {name}")
    while True:
        choice = input_fn("Product [1] > ").strip()
        if not choice:
            return products[0]
        if choice.isdigit() and 1 <= int(choice) <= len(products):
            return products[int(choice) - 1]
        for product in products:
            if product[1].casefold() == choice.casefold():
                return product
        output_fn("Không tìm thấy product. Nhập số hoặc tên đúng như danh sách.")


def _gate_action(input_fn: InputFn, output_fn: OutputFn) -> str:
    while True:
        choice = input_fn("Gate #2 — [a]pprove / [r]eject > ").strip().casefold()
        if choice in {"a", "approve"}:
            return "approve"
        if choice in {"r", "reject"}:
            return "reject"
        output_fn("Chọn a hoặc r.")


def run_interactive(
    runtime: TerminalRuntime,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
) -> None:
    """Run repeated owner-driven investigations until `/quit` or Ctrl+C."""
    output_fn("=" * 68)
    output_fn("HAPPYNEST AGENT TERMINAL — UNDERSTAND → Gate #2 → ACT")
    output_fn("Trace chỉ hiện metadata; câu hỏi được PII-sanitize trước LLM.")
    output_fn(runtime.tracing_status())
    output_fn("=" * 68)
    product_id, product_name = _choose_product(
        runtime.list_products(), input_fn, output_fn
    )
    output_fn(f"Đang dùng product: {product_name}")

    try:
        while True:
            raw = input_fn("\nQuestion (/quit) > ").strip()
            if raw.casefold() in {"/quit", "/exit", "quit", "exit"}:
                break
            if not raw:
                output_fn("Câu hỏi rỗng — nhập lại.")
                continue

            question = runtime.sanitize_question(raw)
            if not question:
                output_fn("Câu hỏi không còn nội dung sau khi sanitize.")
                continue
            if question != raw:
                output_fn("[pii] Đã thay dữ liệu nhạy cảm bằng placeholder.")

            output_fn("[agent] Bắt đầu investigation; trace sẽ xuất hiện bên dưới...")
            try:
                result = runtime.run_understand(product_id, question, output_fn)
                output_fn(f"[agent] run_id={result.run_id}")
                output_fn(
                    f"[Gate #2] {result.title} | confidence={result.confidence:.2f} "
                    f"| evidence={result.evidence_count}"
                )
                output_fn(f"Finding: {result.finding}")
                action = _gate_action(input_fn, output_fn)
                final_status = runtime.decide(result.run_id, action)
                output_fn(f"[Gate #2] final_status={final_status}")

                if final_status in {"approved", "edited"}:
                    wants_act = input_fn("Chạy ACT tạo đề xuất? [y/N] > ").strip().casefold()
                    if wants_act in {"y", "yes"}:
                        summary = runtime.generate_actions(
                            result.insight_id, output_fn
                        )
                        output_fn(
                            f"[ACT] created={summary.created}; "
                            f"skipped={','.join(summary.skipped) or 'none'}"
                        )
                        for function, score, recommendation in summary.top_actions:
                            output_fn(
                                f"  - {function} | priority={score:.3f} | "
                                f"{recommendation}"
                            )
            except Exception as exc:  # noqa: BLE001 — CLI phải quay lại prompt
                output_fn(f"[error] {type(exc).__name__}: {exc}")
            finally:
                runtime.flush()
    except (EOFError, KeyboardInterrupt):
        output_fn("\nĐã dừng terminal.")
    finally:
        runtime.flush()


class _LiveTraceWatcher:
    """Poll permanent trace rows while the synchronous graph is executing."""

    def __init__(
        self,
        output: OutputFn,
        *,
        run_id: uuid.UUID | None = None,
        since: datetime | None = None,
        call_type=None,
    ) -> None:
        self.output = output
        self.run_id = run_id
        self.since = since
        self.call_type = call_type
        self._stop = threading.Event()
        self._seen: set[uuid.UUID] = set()
        self._thread = threading.Thread(
            target=self._loop, name="agent-terminal-traces", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._emit_new()

    def _loop(self) -> None:
        while not self._stop.wait(0.75):
            self._emit_new()

    def _emit_new(self) -> None:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.llm_call_log import LlmCallLog

        conditions = []
        if self.run_id is not None:
            conditions.append(LlmCallLog.analysis_run_id == self.run_id)
        if self.since is not None:
            conditions.append(LlmCallLog.created_at >= self.since)
        if self.call_type is not None:
            conditions.append(LlmCallLog.call_type == self.call_type)
        with SessionLocal() as db:
            rows = db.scalars(
                select(LlmCallLog)
                .where(*conditions)
                .order_by(LlmCallLog.created_at, LlmCallLog.id)
            ).all()
        for row in rows:
            if row.id not in self._seen:
                self._seen.add(row.id)
                self.output(format_trace_row(row))


class RealTerminalRuntime:
    """Adapter from terminal operations to the production DB/agent services."""

    def tracing_status(self) -> str:
        from app.services.tracing import get_langfuse

        try:
            lf = get_langfuse()
            connected = bool(lf is not None and lf.auth_check())
        except Exception:  # noqa: BLE001 — DB trace vẫn dùng được khi dashboard down
            connected = False
        return (
            "Tracing: Langfuse connected + llm_call_logs enabled"
            if connected
            else "Tracing: Langfuse unavailable; llm_call_logs enabled"
        )

    def list_products(self) -> list[tuple[str, str]]:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.product import Product

        with SessionLocal() as db:
            products = db.scalars(select(Product).order_by(Product.created_at)).all()
            return [(str(product.id), product.name) for product in products]

    def sanitize_question(self, raw: str) -> str:
        from app.services.presidio_service import sanitize

        return sanitize(raw).sanitized_text

    def run_understand(
        self, product_id: str, question: str, output: OutputFn
    ) -> TerminalRun:
        from app.core.config import get_settings
        from app.db.session import SessionLocal
        from app.models.analysis_run import AnalysisRun
        from understand_agent import runner

        settings = get_settings()
        with SessionLocal() as db:
            run = AnalysisRun(
                pipeline_version=runner.PIPELINE_VERSION,
                llm_model=settings.LLM_MODEL,
                prompt_version="understand-v1",
                embedding_model=settings.EMBEDDING_MODEL,
                total_count=1,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
        output(f"[agent] run_id={run_id}")

        watcher = _LiveTraceWatcher(output, run_id=run_id)
        watcher.start()
        try:
            runner.submit_or_start(
                run_id,
                uuid.UUID(product_id),
                {"question": question, "trigger_type": "user_question"},
            )
        finally:
            watcher.stop()

        pending = runner.get_run_snapshot(run_id)
        if pending is None:
            raise RuntimeError("Agent không dừng tại Gate #2; kiểm tra server log.")
        insight = pending["insight"]
        return TerminalRun(
            run_id=str(run_id),
            insight_id=str(pending["insight_id"]),
            title=str(insight["title"]),
            finding=str(insight["finding"]),
            confidence=float(insight["finding_confidence"]),
            evidence_count=len(pending.get("evidence", [])),
        )

    def decide(self, run_id: str, action: str) -> str:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.enums import UserRole
        from app.models.user import User
        from understand_agent import runner

        with SessionLocal() as db:
            reviewer = db.scalars(select(User).where(User.role == UserRole.pm)).first()
            if reviewer is None:
                reviewer = db.scalars(select(User).order_by(User.id)).first()
            if reviewer is None:
                raise RuntimeError("Chưa có reviewer user; chạy scripts/seed_users.py.")
            reviewer_id = str(reviewer.id)
        final = runner.resume_with_decision(
            uuid.UUID(run_id),
            {
                "action": action,
                "reason": "Interactive owner terminal",
                "reviewer_id": reviewer_id,
            },
        )
        return str(final.get("final_status") or "unknown")

    def generate_actions(self, insight_id: str, output: OutputFn) -> ActionSummary:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.enums import LlmCallType
        from app.models.insight import Insight
        from app.services import act_agent

        started_at = datetime.now(timezone.utc)
        watcher = _LiveTraceWatcher(
            output, since=started_at, call_type=LlmCallType.act_generate
        )
        watcher.start()
        try:
            with SessionLocal() as db:
                insight = db.get(Insight, uuid.UUID(insight_id))
                if insight is None:
                    raise RuntimeError("Insight không tồn tại.")
                created, skipped, generation_error = act_agent.generate_actions(db, insight)
                if generation_error:
                    output(f"[error] ACT generation failed: {generation_error}")
                    return ActionSummary(
                        created=0, skipped=[], top_actions=[]
                    )
                ordered = sorted(
                    created, key=lambda item: item.priority_score, reverse=True
                )
                top = [
                    (
                        item.function.value,
                        float(item.priority_score),
                        item.recommendation,
                    )
                    for item in ordered[:5]
                ]
                return ActionSummary(
                    created=len(created), skipped=sorted(skipped), top_actions=top
                )
        finally:
            watcher.stop()

    def flush(self) -> None:
        from app.services import tracing

        tracing.flush()
