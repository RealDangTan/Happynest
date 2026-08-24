"""Tests Presidio sanitize — Phase 06 (06-pii-presidio-service.md §3.4).

Phần service-level là UNIT (engine stanza local, không cần DB/internet sau khi
model đã tải ở Phase 01) — chạy trong default suite. Lần đầu trong một pytest
process sẽ mất ~1 phút load vi+en pipeline (singleton dùng chung các test sau).
Phần WIRING chạm DB thật → marker `integration` theo quy ước phase 08.

Ground truth fake 100% (tái dùng tinh thần dataset S1: example.com, dải IP
private, số tuần tự/tổng hợp).
"""

import uuid

import pytest

from app.services.presidio_service import SanitizeResult, mode, sanitize

# ---------------------------------------------------------------- ground truth

# (text, entity_type kỳ vọng, chuỗi raw PII không được sót trong sanitized)
GROUND_TRUTH = [
    ("Liên hệ nguyenvan@example.com ngay nhé", "EMAIL_ADDRESS", "nguyenvan@example.com"),
    ("Gọi hotline 0901234567 giúp tôi", "VN_PHONE", "0901234567"),
    ("Số người nhận là +84912345678 đó", "VN_PHONE", "+84912345678"),
    ("OTP gửi về 0912 345 678 không đến", "VN_PHONE", "0912 345 678"),
    ("CCCD của tôi 012345678901 bị từ chối", "CCCD_12", "012345678901"),
]
# Obvious types đồng bộ định nghĩa pass-criterion S1: EMAIL/PHONE/CCCD.
OBVIOUS = [s for s in GROUND_TRUTH if s[1] != "URL"]

EXTRA_CASES = [
    # URL / IP không nằm trong định nghĩa obvious của S1 nhưng phải mask đúng loại
    ("Xem https://example.com/bai-viet để biết thêm", "<URL>", "https://example.com/bai-viet"),
    ("Máy chủ 192.168.1.10 trả lỗi 500", "<IP_ADDRESS>", "192.168.1.10"),
]


def _sanitize_all():
    return [(text, expected_type, raw, sanitize(text)) for text, expected_type, raw in GROUND_TRUTH]


# ------------------------------------------------------------- service (unit)


class TestSanitizeService:
    def test_obvious_recall_ge_80pct(self):
        """Pass criterion S1: recall EMAIL/PHONE/CCCD ≥ 80%. Hit = entity đúng
        loại phủ trọn span của chuỗi raw trong text gốc."""
        cases = _sanitize_all()
        hits = 0
        for text, etype, raw, result in cases:
            start = text.find(raw)
            assert start >= 0  # sanity: raw phải tồn tại trong text gốc
            if any(
                e.type == etype and e.start <= start and e.end >= start + len(raw)
                for e in result.entities
            ):
                hits += 1
        recall = hits / len(cases)
        assert recall >= 0.8, f"recall {recall:.0%} < 80%: {[c[3].sanitized_text for c in cases]}"

    def test_sanitized_contains_no_raw_pii(self):
        """Không chuỗi raw PII nào (kể cả bỏ khoảng trắng) còn sót trong output."""
        for _, _, raw, result in _sanitize_all() + [
            (t, "", raw_v, sanitize(t)) for t, _, raw_v in EXTRA_CASES
        ]:
            normalized_out = result.sanitized_text.replace(" ", "")
            normalized_raw = raw.replace(" ", "")
            assert normalized_raw not in normalized_out, (
                f"LEAK: '{raw}' còn trong '{result.sanitized_text}'"
            )

    def test_placeholders_correct_type(self):
        expectations = {
            "EMAIL_ADDRESS": "<EMAIL>",
            "VN_PHONE": "<PHONE_NUMBER>",
            "CCCD_12": "<CCCD>",
        }
        for text, etype, raw, result in _sanitize_all():
            if any(e.type == etype for e in result.entities):
                assert expectations[etype] in result.sanitized_text
        # URL/IP qua EXTRA_CASES
        for text, placeholder, raw in EXTRA_CASES:
            out = sanitize(text)
            assert placeholder in out.sanitized_text, f"{placeholder} thiếu trong {out.sanitized_text}"

    def test_entities_metadata_only(self):
        """entities chỉ được chứa {type,start,end,score} — KHÔNG key nào mang text."""
        allowed_keys = {"type", "start", "end", "score"}
        for text, _, _, result in _sanitize_all():
            assert isinstance(result, SanitizeResult)
            for entity in result.entities:
                dump = entity.model_dump()
                assert set(dump.keys()) == allowed_keys, f"key lạ: {dump.keys()}"
                assert all(isinstance(v, (str, int, float)) for v in dump.values())
                # Giá trị type là tên loại ngắn, không thể là payload text
                assert len(dump["type"]) < 30

    def test_clean_text_passthrough(self):
        clean = "Ứng dụng hay nhưng hay lag khi dịch chuyển tab"
        result = sanitize(clean)
        assert result.pii_detected is False
        assert result.entities == []
        assert result.sanitized_text == clean  # giữ nguyên từng ký tự

    def test_cccd_not_doublemasked_as_phone(self):
        """Regression chồng lấn S1: CCCD 12 số chỉ ra <CCCD>, không sinh
        <PHONE_NUMBER> từ 10 số con bên trong."""
        result = sanitize("CCCD 012345678901 của tôi")
        types = [e.type for e in result.entities]
        assert "CCCD_12" in types
        assert "VN_PHONE" not in types
        assert "<PHONE_NUMBER>" not in result.sanitized_text
        assert "<CCCD>" in result.sanitized_text

    def test_person_name_soft_check(self):
        """PERSON usable-with-caveat (S1): NER tiếng Việt yếu hơn pattern.
        Không fail cứng — chỉ báo cáo nếu miss để theo dõi suy giảm."""
        result = sanitize("Tôi là Nguyễn Văn An, tài khoản bị khoá")
        detected = any(e.type == "PERSON" for e in result.entities)
        if not detected:
            print("\n[info] PERSON miss (caveat chấp nhận theo S1) — mode:", mode())

    def test_mode_reports_full_or_fallback(self):
        status = mode()
        assert status["initialized"] is True
        assert status["mode"] in {"full", "regex_only"}
        # Fallback trigger thì decisions.md PHẢI có entry (plan §6) — nhắc bằng flag.
        if status["mode"] == "regex_only":
            pytest.fail(f"NLP fallback đã kích hoạt: {status['nlp_failed_reason']} — phải ghi decisions.md")


# ------------------------------------------------------------ wiring (integration)


@pytest.mark.integration
class TestIngestWiring:
    def test_post_with_pii_is_sanitized_in_db(self, client):
        """DoD mục 4: ingest qua API dòng có PII → DB pii_detected=true,
        sanitized khác raw và không còn chuỗi raw."""
        from sqlalchemy import or_

        from app.db.session import SessionLocal
        from app.models.feedback import Feedback
        from tests.test_ingest import _login_headers

        try:
            from app.models.enums import UserRole

            headers = _login_headers(client, UserRole.pm)
            content = "Liên hệ tran.van.b@example.com hoặc 0987654321 để được hỗ trợ"
            response = client.post(
                "/api/feedbacks",
                json={"source": "app_review", "content": content, "external_ref": f"piiwire-{uuid.uuid4().hex[:8]}"},
                headers=headers,
            )
            assert response.status_code == 201, response.text
            body = response.json()
            # API mặc định: sanitized visible, raw KHÔNG
            assert body["pii_detected"] is True
            assert body["sanitized_content"] != content
            assert "@example.com" not in body["sanitized_content"]

            with SessionLocal() as db:
                row = db.get(Feedback, uuid.UUID(body["id"]))
                assert row.pii_detected is True
                assert row.raw_content == content
                assert row.sanitized_content != row.raw_content
                assert "0987654321" not in (row.sanitized_content or "")
                # entities metadata-only trong JSONB
                assert row.pii_entities
                for entity in row.pii_entities:
                    assert set(entity.keys()) == {"type", "start", "end", "score"}
        finally:
            with SessionLocal() as db:
                db.query(Feedback).filter(
                    or_(Feedback.external_ref.like("piiwire-%"))
                ).delete(synchronize_session=False)
                db.commit()
