"""Synthetic ACT proposals shared by offline and integration tests."""


def support_draft(evidence_ids=None, kind="investigate"):
    return {
        "kind": kind,
        "evidence_ids": evidence_ids or [],
        "perspectives": [
            {"lens": "ux", "assessment": "Cho phép người dùng sửa câu trả lời sai."},
            {"lens": "product", "assessment": "Kiểm chứng nhu cầu trước khi mở rộng."},
        ],
        "references": [
            {"card_id": "hax-correction", "application": "Thử cơ chế chỉnh sửa câu trả lời."},
            {"card_id": "rice-confidence", "application": "Ghi rõ căn cứ và bất định của ước lượng."},
        ],
        "source_gap": None,
        "alternative": {
            "recommendation": "Thay model ngay cho toàn bộ người dùng.",
            "tradeoff": "Tốn chi phí và chưa kiểm chứng nguyên nhân.",
        },
        "tradeoff": "Thử nghiệm nhỏ cần thời gian nhưng giảm rủi ro chọn sai giải pháp.",
        "assumptions": ["Khó chỉnh sửa là một điểm nghẽn cần kiểm chứng."],
        "success_criteria": "Đo tỷ lệ hoàn thành tác vụ sửa lỗi; xác định baseline trước thử nghiệm.",
        "estimate_basis": "Ước lượng sơ bộ, cần xác nhận effort với Engineering.",
    }


def proposal_payload(evidence_ids=None, kind="investigate"):
    return {"functions": [{
        "function": "ENGINEERING", "relevance": 0.95,
        "recommendation": "Thử cơ chế sửa câu trả lời trên một nhóm nhỏ.",
        "rationale": "Insight đã duyệt ghi nhận khó khăn khi sửa lỗi AI.",
        "impact": 7, "effort": 4, "urgency": 6, "confidence": 0.65,
        "decision_support": support_draft(evidence_ids, kind),
    }]}
