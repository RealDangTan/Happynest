"""Classifier v1 — phân loại feedback đã sanitize bằng LLM.

Prompt version hóa (`PROMPT_VERSION`): prompt kém trên sample thật → ra v2,
KHÔNG sửa v1 — giữ khả năng so sánh A/B theo plan §6.

Reshape VoC OS 2026-08-28: công thức `compute_requires_human_review` bị
BỎ cùng feedback-level HITL (routes/review.py đã strip) — output ghi thẳng
`feedback.ai_analysis` JSONB ở runner; plan 23 sẽ đổi output sang taxonomy-
aware (topics khớp bảng taxonomies).

⚠️ PII boundary: `classify_feedback` chỉ nhận text ĐÃ sanitize. Raw content
không bao giờ đi qua hàm này vào prompt/log/trace.
"""

from app.models.enums import LlmCallType
from app.schemas.taxonomy import Classification
from app.services.llm_client import chat_structured

PROMPT_VERSION = "v1"

SYSTEM_PROMPT_V1 = """Bạn là chuyên gia phân loại phản hồi người dùng về một sản phẩm có tính năng AI. \
Văn phong làm việc: tiếng Việt, trộn thuật ngữ kỹ thuật tiếng Anh là bình thường.

Nhiệm vụ: với MỖI feedback, trả về JSON object gồm:
- categories: 1..n nhãn chủ đề tự do (vd: "dịch thuật", "hiệu năng", "đăng nhập", "UI", "xuất file")
- ai_issue: loại vấn đề AI nếu có — một trong hallucination | inaccuracy | bias | safety | privacy | performance | other; null nếu không phải vấn đề của AI
- sentiment: positive | negative | neutral | mixed
- severity: mức nghiêm trọng theo rubric:
  * low: phiền nhỏ, thẩm mỹ, wording, không ảnh hưởng kết quả
  * medium: ảnh hưởng một phần trải nghiệm, có cách workaround
  * high: chặn tính năng chính, mất dữ liệu tạm thời, kết quả sai rõ ràng phải làm lại
  * critical: nguy cơ an toàn/bảo mật, mất dữ liệu THẬT, hệ quả pháp lý, nội dung độc hại
- safety_issue: true nếu feedback liên quan an toàn người dùng, bảo mật, hoặc nội dung độc hại do AI sinh ra — kể cả khi severity chưa tới critical
- confidence: tự đánh giá độ tin cậy [0..1] của toàn bộ phân loại này; thấp (<0.6) khi feedback mơ hồ, quá ngắn, hoặc chồng chéo nhiều nhãn
- rationale: giải thích ngắn gọn ≤ 2 câu tiếng Việt vì sao phân loại như vậy

Chỉ trả về JSON object, không text thừa."""


def classify_feedback(
    sanitized_text: str,
    few_shot: list[dict] | None = None,
    *,
    feedback_id=None,
    analysis_run_id=None,
) -> Classification:
    """Phân loại một feedback ĐÃ SANITIZE thành `Classification`.

    `few_shot`: list dict {"text": str, "label": Classification-like dict} —
    param tồn tại từ v1 để loop correction (phase sau) cắm vào mà không đổi chữ ký.

    `feedback_id`/`analysis_run_id` (Phase 09 thêm): passthrough metadata vào
    llm_call_logs/Langfuse để truy vết call theo run — không đổi hành vi phân loại.
    """
    user_parts: list[str] = []
    for ex in few_shot or []:
        user_parts.append(
            f"Ví dụ:\nFeedback: {ex['text']}\nPhân loại mong muốn: "
            f"{ex['label']}\n"
        )
    user_parts.append(f"Feedback cần phân loại:\n{sanitized_text}")
    return chat_structured(
        SYSTEM_PROMPT_V1,
        "\n".join(user_parts),
        Classification,
        call_type=LlmCallType.classify,
        prompt_version=PROMPT_VERSION,
        feedback_id=feedback_id,
        analysis_run_id=analysis_run_id,
    )
