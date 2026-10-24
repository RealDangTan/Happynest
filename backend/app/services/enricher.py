"""Enricher v3 — JEV-role engine (plan 32; spec Listen 2026-10-07 §3–§6).

Nguyên tắc spec: **GPT discovers the label space, JEV applies the label space
at scale.** Engine enrich là task ĐÓNG:
- topics CHỈ chọn từ Active Taxonomy (slug list) — KHÔNG tự bịa topic;
- confidence topic < `ENRICH_TOPIC_CONFIDENCE_FLOOR` (env, default 0.60) →
  UNCATEGORIZED (topics=[], giữ lại feedback);
- emotions rỗng → ["neutral"] (fallback chốt ở review S7);
- GPT KHÔNG nằm trong per-record runtime.

Engine dispatch theo `ENRICH_ENGINE` (KHÔNG silent-fallback giữa 2 engine):
- `llm`  → `chat_structured`, model qua `MODEL_ENRICH` (plan 30);
- `jev`  → `jev_client.systemone_enrich` — System One native PER-ITEM
  (owner 2026-10-22: bỏ batch chat; mỗi feedback một request, S7 đo
  p95 ~1.06s/request).

⚠️ PII boundary: `enrich_feedback` chỉ nhận text ĐÃ SANITIZE — raw content
không bao giờ đi qua hàm này vào prompt/log/trace.
"""

from app.core.config import get_settings
from app.models.enums import LlmCallType
from app.schemas.enrichment import EnrichmentOut
from app.services.llm_client import chat_structured

PROMPT_VERSION = "v3"

_SYSTEM_PROMPT = """Bạn là bộ phân loại ĐÓNG (closed-set) cho phản hồi người dùng về một sản phẩm có tính năng AI. \
Văn phong làm việc: tiếng Việt, trộn thuật ngữ kỹ thuật tiếng Anh là bình thường. \
Bạn KHÔNG được sáng tạo nhãn ngoài các tập đóng được cung cấp.

Với MỖI feedback, trả về JSON object gồm:
- topics: TỐI ĐA 3 mục {id, probability} — id PHẢI là slug nằm trong "Active taxonomy" được cung cấp; \
KHÔNG BAO GIỜ bịa id mới hay đoán từ ngoài danh sách; sắp giảm dần theo probability; \
để mảng RỖNG nếu không topic nào khớp đủ tốt (đừng ép chọn).
- sentiment: positive | negative | neutral | mixed
- emotions: TỐI ĐA 3 mục {label, probability}; label CHỈ một trong: frustration | anger | disappointment | \
confusion | anxiety | satisfaction | delight | neutral; multi-label được phép (vd frustrated VÀ angry cùng lúc); \
mảng rỗng khi không rõ.
- intent: một trong bug_report | feature_request | question | complaint | praise | other
- severity: mức nghiêm trọng theo rubric:
  * low: phiền nhỏ, thẩm mỹ, wording, không ảnh hưởng kết quả
  * medium: ảnh hưởng một phần trải nghiệm, có cách workaround
  * high: chặn tính năng chính, mất dữ liệu tạm thời, kết quả sai rõ ràng phải làm lại
  * critical: nguy cơ an toàn/bảo mật, mất dữ liệu THẬT, hệ quả pháp lý, nội dung độc hại
- safety_issue: true nếu liên quan an toàn người dùng, bảo mật, hoặc nội dung độc hại do AI sinh ra
- ai_issue: loại vấn đề của AI nếu có — hallucination | inaccuracy | bias | safety | privacy | performance | other; null nếu không phải
- confidence: độ tin cậy [0..1] của TOÀN BỘ phân loại này; thấp (<0.6) khi feedback mơ hồ, quá ngắn, chồng chéo nhiều nhãn
- rationale: giải thích ≤ 2 câu tiếng Việt

Chỉ trả về JSON object, không text thừa."""


def _taxonomy_block(
    taxonomy_labels: list[tuple[str, str, str | None]],
) -> str:
    """Mỗi dòng `- slug — Name (vi: …)`: slug là id duy nhất được phép trả;
    `name` tiếng Anh canonical là nhãn codebook; gloss tiếng Việt (`name_vi`,
    khi có và khác name) giúp khớp feedback code-switching Việt–Anh."""
    lines = "\n".join(
        f"- {slug} — {name} (vi: {name_vi})" if name_vi and name_vi != name else f"- {slug} — {name}"
        for slug, name, name_vi in taxonomy_labels
    )
    return (
        "Active taxonomy (id = slug — CHỈ được dùng các id này cho topics):\n"
        f"{lines}\n\n"
    )


def finalize_enrichment(result: EnrichmentOut, *, taxonomy_version: int) -> dict:
    """Post-process RAW output → JSONB `ai_analysis` cuối cùng (shape v3).

    - threshold: topic probability < `ENRICH_TOPIC_CONFIDENCE_FLOOR` bị cắt;
      rỗng sau cắt → uncategorized=True, topics=[].
    - emotions rỗng → ["neutral"].
    - `topic_confidence` = probability cao nhất còn giữ (None khi uncategorized).
    """
    floor = get_settings().ENRICH_TOPIC_CONFIDENCE_FLOOR
    kept = sorted(
        (t for t in result.topics if t.probability >= floor),
        key=lambda t: t.probability,
        reverse=True,
    )
    emotions = [e.label.value for e in result.emotions if e.label.value != "neutral"] or [
        "neutral"
    ]
    return {
        "topics": [t.id for t in kept],
        "topic_scores": [
            {"id": t.id, "probability": round(t.probability, 4)} for t in kept
        ],
        "topic_confidence": kept[0].probability if kept else None,
        "uncategorized": not kept,
        "sentiment": result.sentiment.value,
        "emotions": emotions,
        "emotion_scores": [
            {"label": e.label.value, "probability": round(e.probability, 4)}
            for e in result.emotions
        ],
        "intent": result.intent.value,
        "severity": result.severity.value,
        "safety_issue": result.safety_issue,
        "ai_issue": result.ai_issue.value if result.ai_issue else None,
        "confidence": result.confidence,
        "rationale": result.rationale,
        "taxonomy_version": taxonomy_version,
        "analysis_version": "enrich-v3",
    }


def active_prompt_version() -> str:
    """prompt_version của engine ĐANG CHẠY — snapshot vào analysis_runs."""
    if get_settings().ENRICH_ENGINE == "jev":
        from app.services.jev_client import JEV_PROMPT_VERSION

        return JEV_PROMPT_VERSION
    return PROMPT_VERSION


def enrich_feedback(
    sanitized_text: str,
    taxonomy_labels: list[tuple[str, str, str | None]],
    *,
    taxonomy_version: int = 1,
    feedback_id=None,
    analysis_run_id=None,
    session_factory=None,
) -> dict:
    """Enrich MỘT feedback ĐÃ SANITIZE → JSONB `ai_analysis` (shape v3).

    `taxonomy_labels`: [(slug, name, name_vi)] từ
    `taxonomy_service.get_taxonomy_labels`. Dispatch theo `ENRICH_ENGINE` —
    đường jev không fallback về llm.
    """
    if get_settings().ENRICH_ENGINE == "jev":
        from app.services.jev_client import systemone_enrich

        return systemone_enrich(
            sanitized_text,
            taxonomy_labels,
            taxonomy_version=taxonomy_version,
            feedback_id=feedback_id,
            analysis_run_id=analysis_run_id,
            session_factory=session_factory,
        )
    result = chat_structured(
        _SYSTEM_PROMPT,
        f"{_taxonomy_block(taxonomy_labels)}Feedback cần phân loại:\n{sanitized_text}",
        EnrichmentOut,
        call_type=LlmCallType.enrich,
        prompt_version=PROMPT_VERSION,
        feedback_id=feedback_id,
        analysis_run_id=analysis_run_id,
    )
    return finalize_enrichment(result, taxonomy_version=taxonomy_version)
