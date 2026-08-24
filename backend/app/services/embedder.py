"""Embedder — module DUY NHẤT gọi `/v1/embeddings` (execute-plan §1, plan 08).

Contracts khóa §7:
    embed_texts(texts: list[str]) -> list[list[float]]   # batch ≤2048, retry backoff
    embed_one(text: str) -> list[float]

⚠️ PII boundary: input PHẢI là text ĐÃ sanitize — cùng nguyên tắc llm_client
(Phase 07). Module không nhận raw content dưới mọi hình thức.

Vector luôn đi kèm `embedding_model` + `embedding_dim` per row (locked stack
AGENTS.md) — set qua store_embedding(), đừng gán cột tay rải rác.

Không ANN index: dataset ≤1500 rows → exact scan là đủ (xem route /similar).
"""

import logging
import time
from collections.abc import Sequence

from openai import OpenAI
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import LlmCallType
from app.services.tracing import write_llm_call_log

logger = logging.getLogger(__name__)

#: Giới hạn số input mỗi call API (khóa theo contract §7).
EMBED_BATCH_MAX_INPUTS = 2048


class EmbeddingDimError(ValueError):
    """Provider trả vector lệch `settings.EMBEDDING_DIM` — chặn sớm trước khi lưu DB."""


def _client() -> OpenAI:
    """OpenAI-compatible client cho embeddings: EMBEDDING_* ưu tiên, fallback LLM_*
    (decisions.md 2026-08-24 — alias env người dùng)."""
    settings = get_settings()
    base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    return OpenAI(base_url=base_url, api_key=api_key)


_session_factory = SessionLocal  # unit test monkeypatch điểm này


def _log_call(
    *,
    latency_ms: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> None:
    """Ghi llm_call_logs (call_type=embed) bằng session ngắn hạn riêng —
    không ràng buộc transaction của caller. Lỗi logging KHÔNG được giết flow."""
    try:
        with _session_factory() as session:
            write_llm_call_log(
                session,
                call_type=LlmCallType.embed,
                prompt_version=get_settings().PROMPT_VERSION,
                model=get_settings().EMBEDDING_MODEL,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error[:500] if error else None,
            )
            session.commit()
    except Exception:  # noqa: BLE001 - logging best-effort
        logger.warning("embedder: ghi llm_call_logs thất bại", exc_info=True)


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _create_embeddings(client: OpenAI, model: str, batch: list[str]):
    """1 call network có retry backoff. MỖI attempt (kể cả lỗi) ghi 1 row log."""
    start = time.perf_counter()
    try:
        response = client.embeddings.create(model=model, input=batch)
    except Exception as exc:
        latency = int((time.perf_counter() - start) * 1000)
        _log_call(latency_ms=latency, error=f"{type(exc).__name__}: {exc}")
        raise
    latency = int((time.perf_counter() - start) * 1000)
    usage = getattr(response, "usage", None)
    _log_call(
        latency_ms=latency,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )
    return response


def _validate_dims(vectors: Sequence[Sequence[float]]) -> None:
    expected = get_settings().EMBEDDING_DIM
    for i, vec in enumerate(vectors):
        if len(vec) != expected:
            raise EmbeddingDimError(
                f"Embedding thứ {i} có {len(vec)} chiều, hợp đồng yêu cầu "
                f"{expected} (EMBEDDING_DIM). Provider đổi model? Xem decisions.md."
            )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text đã sanitize; chia batch ≤2048, ghép ĐÚNG thứ tự."""
    if not texts:
        return []
    client = _client()
    model = get_settings().EMBEDDING_MODEL
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_MAX_INPUTS):
        batch = texts[start : start + EMBED_BATCH_MAX_INPUTS]
        response = _create_embeddings(client, model, batch)
        # API trả .data theo .index — sort lại phòng provider trả lệch thứ tự.
        ordered = sorted(response.data, key=lambda d: d.index)
        batch_vectors = [item.embedding for item in ordered]
        _validate_dims(batch_vectors)
        vectors.extend(batch_vectors)
    return vectors


def embed_one(text: str) -> list[float]:
    """Embed 1 text đã sanitize."""
    return embed_texts([text])[0]


def store_embedding(session: Session, feedback, vector: Sequence[float]) -> None:
    """Set ĐỒNG THỜI 3 cột trên row Feedback (quyết định §1 plan 08):
    embedding + embedding_model + embedding_dim luôn đi cùng nhau.
    Không commit — transaction thuộc về caller."""
    expected = get_settings().EMBEDDING_DIM
    if len(vector) != expected:
        raise EmbeddingDimError(
            f"store_embedding: vector {len(vector)} chiều != EMBEDDING_DIM={expected}"
        )
    feedback.embedding = list(vector)
    feedback.embedding_model = get_settings().EMBEDDING_MODEL
    feedback.embedding_dim = len(vector)
