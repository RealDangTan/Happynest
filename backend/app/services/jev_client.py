"""JEV System One client — engine per-item native (ENRICH_ENGINE=jev).

Owner directive 2026-10-22 (decisions.md cùng ngày): enrichment chạy
**SINGULAR** — mỗi feedback ĐÃ SANITIZE = MỘT request
`POST {base}/systemone` mang N câu hỏi typed song song (docs TypeSafe
`/api`; S7 chứng thực p95 ~1.06s/request trên cùng endpoint):
- Noul   (xác suất [0..1]) → topics multi-label + emotions multi-label + safety
- Choice (tập đóng)        → sentiment + intent + ai_issue
- Score  (thang mức)       → severity

Endpoint mặc định suy từ `LLM_BASE_URL` (OpenRouter `…/api/v1` →
`…/api/v1/systemone` — S7 correction 2026-10-09: cùng key OpenRouter dùng
được); `JEV_API_BASE` override khi gọi thẳng api.typesafe.ai. Key:
`JEV_API_KEY` → fallback `LLM_API_KEY`. KHÔNG silent-fallback về engine
`llm` — mọi lỗi raise `LLMStructureError` để runner xử lý item-level như
đường chat.

Map answer → `EnrichmentOut`: topics/emotions lấy Noul của TỪNG nhãn
(top-3 theo xác suất — schema khóa max 3); severity = round(score) vào
thang low→critical (phương pháp S7); `confidence` KHÔNG tự báo nữa mà lấy
min xác suất các lựa chọn/chỉ dấu (chủ động thấp → HITL giữ lại); rationale
là chuỗi deterministic từ xác suất — không text model sinh (chặt hơn biên PII).

⚠️ PII boundary: `state` PHẢI là text ĐÃ SANITIZE — hợp đồng như llm_client;
caller (sanitize → enrich) chịu trách nhiệm.
"""

import math
import time
from threading import Lock
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import AiIssue, Emotion, Intent, LlmCallType, Sentiment, Severity
from app.schemas.enrichment import EmotionScore, EnrichmentOut, TopicScore
from app.services.llm_client import LLMStructureError, _record_attempt

logger = get_logger(__name__)

JEV_PROMPT_VERSION = "jev-v1"

#: Hệ nhãn đóng — trùng khớp enum (`app/models/enums.py`); severity đánh chỉ
#: số index = round(score).
_SEVERITY_LADDER = [s.value for s in Severity]
_SENTIMENTS = [s.value for s in Sentiment]
_INTENTS: dict[str, str] = {
    Intent.bug_report.value: "Báo lỗi/hỏng hóc",
    Intent.feature_request.value: "Đề xuất tính năng mới",
    Intent.question.value: "Hỏi cách dùng/thông tin",
    Intent.complaint.value: "Khiếu nại trải nghiệm",
    Intent.praise.value: "Khen",
    Intent.other.value: "Khác",
}
_AI_ISSUE_NONE = "none"

_TOPIC_PREFIX = "topic::"
_EMOTION_PREFIX = "emotion::"

_MAX_RETRIES = 3
_TIMEOUT_S = 120.0
_http_client: httpx.Client | None = None
_client_lock = Lock()


def _get_client() -> httpx.Client:
    # httpx.Client's pool can be shared by threads; headers stay request-local.
    global _http_client
    with _client_lock:
        if _http_client is None:
            _http_client = httpx.Client(timeout=_TIMEOUT_S)
        return _http_client


def close_client() -> None:
    global _http_client
    with _client_lock:
        if _http_client is not None:
            _http_client.close()
            _http_client = None


def build_questions(
    topic_labels: list[tuple[str, str, str | None]],
) -> dict[str, dict[str, Any]]:
    """Bộ câu hỏi cho MỘT feedback — 1 request, N câu song song (spec §API).

    `topic_labels` = (slug, name, name_vi) của Active Taxonomy; topic mới
    KHÔNG được hỏi (closed-set — engine không tự bịa nhãn). Câu hỏi nêu cả
    tên canonical (EN) + nhãn hiển thị (VI) để khớp feedback code-switching,
    nhưng id trả về vẫn CHỈ là slug.
    """
    questions: dict[str, dict[str, Any]] = {
        "sentiment": {
            "type": "choice",
            "instructions": "Sentiment của feedback người dùng về sản phẩm (có thể trộn VI/EN, teencode).",
            "criteria": {s: None for s in _SENTIMENTS},
        },
        "intent": {
            "type": "choice",
            "instructions": "Ý định chính của feedback.",
            "criteria": dict(_INTENTS),
        },
        "severity": {
            "type": "score",
            "instructions": "Mức nghiêm trọng của vấn đề được mô tả: low (phiền nhỏ) → critical (an toàn/mất dữ liệu thật).",
            "criteria": list(_SEVERITY_LADDER),
        },
        "safety": {
            "type": "noul",
            "instructions": "Feedback có liên quan an toàn người dùng, bảo mật, hoặc nội dung độc hại do AI sinh ra không?",
            "criteria": {"true": "Có", "false": "Không"},
        },
        "ai_issue": {
            "type": "choice",
            "instructions": "Loại vấn đề của tính năng AI nếu có; chọn 'none' khi không phải vấn đề AI.",
            "criteria": {
                _AI_ISSUE_NONE: "Không có vấn đề AI",
                AiIssue.hallucination.value: "AI bịa dữ liệu/nguồn",
                AiIssue.inaccuracy.value: "AI trả lời sai sự thật",
                AiIssue.bias.value: "AI thiên lệch/phân biệt",
                AiIssue.safety.value: "AI gây rủi ro an toàn",
                AiIssue.privacy.value: "AI lộ/xử lý sai dữ liệu cá nhân",
                AiIssue.performance.value: "AI chậm/không ổn định",
                AiIssue.other.value: "Vấn đề AI khác",
            },
        },
    }
    for slug, name, name_vi in topic_labels:
        label = name or slug
        if name_vi and name_vi != name:
            label = f"{label} (vi: {name_vi})"
        questions[f"{_TOPIC_PREFIX}{slug}"] = {
            "type": "noul",
            "instructions": f"Feedback này có thuộc chủ đề '{label}' không? (id chủ đề: {slug})",
            "criteria": {"true": "Nội dung nói đúng vấn đề này", "false": "Không liên quan"},
        }
    for emo in Emotion:
        questions[f"{_EMOTION_PREFIX}{emo.value}"] = {
            "type": "noul",
            "instructions": f"Feedback có thể hiện cảm xúc '{emo.value}' không?",
            "criteria": {"true": "Có", "false": "Không"},
        }
    return questions


def _noul(answers: dict[str, Any], qid: str) -> float:
    value = answers.get(qid, {}).get("noul")
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise LLMStructureError(f"systemone: noul '{qid}' không hợp lệ.")
    return float(value)


def _choice(answers: dict[str, Any], qid: str, allowed: set[str]) -> tuple[str, float]:
    answer = answers.get(qid, {})
    choice = answer.get("choice")
    probabilities = answer.get("probabilities")
    if choice not in allowed or not isinstance(probabilities, dict):
        raise LLMStructureError(f"systemone: choice '{qid}' không hợp lệ.")
    probability = probabilities.get(choice)
    if not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise LLMStructureError(f"systemone: choice '{qid}' thiếu xác suất lựa chọn.")
    return str(choice), float(probability)


def answers_to_enrichment(
    answers: dict[str, Any], taxonomy_slugs: list[str]
) -> EnrichmentOut:
    """Parse `answers` System One → `EnrichmentOut` (chưa finalize)."""
    sentiment, sentiment_p = _choice(answers, "sentiment", set(_SENTIMENTS))
    intent, intent_p = _choice(answers, "intent", set(_INTENTS))
    ai_choice, _ = _choice(answers, "ai_issue", {_AI_ISSUE_NONE} | {a.value for a in AiIssue})
    ai_issue: AiIssue | None = None if ai_choice == _AI_ISSUE_NONE else AiIssue(ai_choice)

    score = answers.get("severity", {}).get("score")
    if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= len(_SEVERITY_LADDER) - 1:
        raise LLMStructureError("systemone: severity score ngoài thang low→critical.")
    severity_index = round(float(score))
    severity_answer = answers.get("severity", {})
    severity_probabilities = severity_answer.get("probabilities")
    if not isinstance(severity_probabilities, dict):
        raise LLMStructureError("systemone: severity thiếu probabilities.")
    severity_p_raw = severity_probabilities.get(str(severity_index))
    if not isinstance(severity_p_raw, (int, float)) or not 0 <= severity_p_raw <= 1:
        raise LLMStructureError("systemone: severity xác suất không hợp lệ.")
    severity_p = float(severity_p_raw)

    topics = sorted(
        (
            TopicScore(id=slug, probability=_noul(answers, f"{_TOPIC_PREFIX}{slug}"))
            for slug in taxonomy_slugs
        ),
        key=lambda t: t.probability,
        reverse=True,
    )[:3]
    emotions = sorted(
        (
            EmotionScore(label=emo, probability=_noul(answers, f"{_EMOTION_PREFIX}{emo.value}"))
            for emo in Emotion
        ),
        key=lambda e: e.probability,
        reverse=True,
    )[:3]
    safety = _noul(answers, "safety")

    # Confidence = min xác suất các LỰA CHỌN phân loại — chủ động THẤP để HITL
    # giữ lại (System One không có "tự đánh giá tin cậy toàn classification" như
    # chat). Noul `safety` KHÔNG nằm đây: nó là mức liên quan an toàn, không phải
    # độ tin cậy — safety thấp là trạng thái bình thường, không phải bất định.
    confidence_parts = [sentiment_p, intent_p, severity_p]
    if topics:
        confidence_parts.append(topics[0].probability)
    if emotions:
        confidence_parts.append(emotions[0].probability)
    confidence = round(min(confidence_parts), 4)

    rationale = (
        f"JEV System One per-item: sentiment={sentiment_p:.2f}, intent={intent_p:.2f}, "
        f"severity={severity_p:.2f}, safety={safety:.2f}."
    )
    return EnrichmentOut(
        topics=topics,
        sentiment=Sentiment(sentiment),
        emotions=emotions,
        intent=Intent(intent),
        severity=Severity(_SEVERITY_LADDER[severity_index]),
        safety_issue=safety >= 0.5,
        ai_issue=ai_issue,
        confidence=confidence,
        rationale=rationale,
    )


def _endpoint(settings: Any) -> str:
    base = settings.JEV_API_BASE or settings.LLM_BASE_URL
    if not base:
        raise LLMStructureError("systemone: thiếu JEV_API_BASE/LLM_BASE_URL.")
    return base.rstrip("/") + "/systemone"


def _api_key(settings: Any) -> str:
    return settings.JEV_API_KEY or settings.LLM_API_KEY


def _post_systemone(payload: dict[str, Any], *, endpoint: str, api_key: str) -> dict[str, Any]:
    """Một request System One; 429/529 backoff tối đa {_MAX_RETRIES} lần (S7)."""
    client = _get_client()
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise LLMStructureError(f"systemone transport: {type(exc).__name__}") from exc
        if response.status_code in (429, 529) and attempt < _MAX_RETRIES:
            time.sleep(2**attempt)
            continue
        if response.status_code != 200:
            raise LLMStructureError(f"systemone HTTP {response.status_code}.")
        return response.json()
    raise LLMStructureError("systemone: quá số lần retry rate-limit.")  # pragma: no cover


def systemone_enrich(
    sanitized_text: str,
    taxonomy_labels: list[tuple[str, str, str | None]],
    *,
    taxonomy_version: int = 1,
    feedback_id: Any | None = None,
    analysis_run_id: Any | None = None,
    session_factory: Any | None = None,
) -> dict:
    """Enrich MỘT feedback ĐÃ SANITIZE qua System One → JSONB `ai_analysis`.

    `taxonomy_labels`: [(slug, name, name_vi)] — slug vào question id,
    name/name_vi chỉ để câu hỏi dễ khớp hơn; trả shape đã qua
    `finalize_enrichment` (threshold + neutral).
    """
    from app.db.session import SessionLocal

    settings = get_settings()
    slugs = [slug for slug, _, _ in taxonomy_labels]
    payload = {
        "model": settings.JEV_MODEL,
        "state": sanitized_text,
        "questions": build_questions(taxonomy_labels),
    }
    t0 = time.perf_counter()
    try:
        body = _post_systemone(
            payload,
            endpoint=_endpoint(settings),
            api_key=_api_key(settings),
        )
    except LLMStructureError as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        _record_attempt(
            name=f"enrich:SystemOne({settings.JEV_MODEL})",
            input_text_sanitized=sanitized_text,
            output_text="",
            schema_name="EnrichmentOut",
            call_type=LlmCallType.enrich,
            prompt_version=JEV_PROMPT_VERSION,
            model=settings.JEV_MODEL,
            latency_ms=latency,
            usage=None,
            error=str(exc)[:500],
            feedback_id=feedback_id,
            analysis_run_id=analysis_run_id,
            session_factory=session_factory or SessionLocal,
        )
        raise

    latency = int((time.perf_counter() - t0) * 1000)
    answers = body.get("answers")
    if not isinstance(answers, dict):
        answers = {}
    try:
        result = answers_to_enrichment(answers, slugs)
    except LLMStructureError as exc:
        usage = body.get("usage") or {}
        _record_attempt(
            name=f"enrich:SystemOne({settings.JEV_MODEL})",
            input_text_sanitized=sanitized_text,
            output_text="",
            schema_name="EnrichmentOut",
            call_type=LlmCallType.enrich,
            prompt_version=JEV_PROMPT_VERSION,
            model=settings.JEV_MODEL,
            latency_ms=latency,
            usage={
                "prompt": int(usage.get("prompt_tokens", usage.get("input_tokens")) or 0),
                "completion": int(usage.get("completion_tokens", usage.get("output_tokens")) or 0),
            },
            error=str(exc)[:500],
            feedback_id=feedback_id,
            analysis_run_id=analysis_run_id,
            session_factory=session_factory or SessionLocal,
        )
        raise

    usage = body.get("usage") or {}
    usage_norm = {
        "prompt": int(usage.get("prompt_tokens", usage.get("input_tokens")) or 0),
        "completion": int(usage.get("completion_tokens", usage.get("output_tokens")) or 0),
    }
    _record_attempt(
        name=f"enrich:SystemOne({settings.JEV_MODEL})",
        input_text_sanitized=sanitized_text,
        output_text=body.get("model") or settings.JEV_MODEL,
        schema_name="EnrichmentOut",
        call_type=LlmCallType.enrich,
        prompt_version=JEV_PROMPT_VERSION,
        model=settings.JEV_MODEL,
        latency_ms=latency,
        usage=usage_norm,
        error=None,
        feedback_id=feedback_id,
        analysis_run_id=analysis_run_id,
        session_factory=session_factory or SessionLocal,
    )

    from app.services.enricher import finalize_enrichment

    return finalize_enrichment(result, taxonomy_version=taxonomy_version)
