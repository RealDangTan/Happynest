"""Unit contracts for the owner-facing interactive agent terminal."""

from types import SimpleNamespace

from app.services.agent_terminal import (
    ActionSummary,
    TerminalRun,
    format_trace_row,
    run_interactive,
)


class FakeRuntime:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.decisions: list[str] = []
        self.action_requests: list[str] = []

    def tracing_status(self) -> str:
        return "Langfuse connected + llm_call_logs enabled"

    def list_products(self) -> list[tuple[str, str]]:
        return [("product-1", "Happynest")]

    def sanitize_question(self, raw: str) -> str:
        return raw.replace("test@example.com", "<EMAIL>")

    def run_understand(self, product_id: str, question: str, output) -> TerminalRun:
        self.questions.append(question)
        output(
            format_trace_row(
                SimpleNamespace(
                    call_type=SimpleNamespace(value="plan"),
                    error=None,
                    latency_ms=120,
                    prompt_tokens=10,
                    completion_tokens=4,
                    model="demo-model",
                )
            )
        )
        return TerminalRun(
            run_id="run-1",
            insight_id="insight-1",
            title="Synthetic finding",
            finding="There is enough evidence to review.",
            confidence=0.8,
            evidence_count=2,
        )

    def decide(self, run_id: str, action: str) -> str:
        self.decisions.append(action)
        return "approved" if action == "approve" else "rejected"

    def generate_actions(self, insight_id: str, output) -> ActionSummary:
        self.action_requests.append(insight_id)
        return ActionSummary(created=1, skipped=["LEGAL"], top_actions=[])

    def flush(self) -> None:
        return None


def test_session_sanitizes_before_agent_and_allows_owner_to_approve():
    runtime = FakeRuntime()
    inputs = iter(["", "contact test@example.com", "a", "n", "/quit"])
    output: list[str] = []

    run_interactive(runtime, lambda prompt: next(inputs), output.append)

    assert runtime.questions == ["contact <EMAIL>"]
    assert runtime.decisions == ["approve"]
    assert runtime.action_requests == []
    assert any("[trace] plan | OK | 120ms" in line for line in output)
    assert any("Gate #2" in line and "Synthetic finding" in line for line in output)


def test_invalid_gate_choice_is_rejected_before_resume():
    runtime = FakeRuntime()
    inputs = iter(["", "test question", "x", "r", "/quit"])
    output: list[str] = []

    run_interactive(runtime, lambda prompt: next(inputs), output.append)

    assert runtime.decisions == ["reject"]
    assert any("Chọn a hoặc r" in line for line in output)


def test_trace_line_contains_metadata_but_not_payload():
    trace = SimpleNamespace(
        call_type=SimpleNamespace(value="plan"),
        error=None,
        latency_ms=120,
        prompt_tokens=10,
        completion_tokens=4,
        model="demo-model",
        input="raw input must not appear",
        output="raw output must not appear",
    )

    line = format_trace_row(trace)

    assert line == "[trace] plan | OK | 120ms | tokens 10→4 | demo-model"
    assert "raw input" not in line
    assert "raw output" not in line
