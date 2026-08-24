"""Spike S1 — Presidio + Stanza("vi") + regex có bắt đủ PII trong mẫu VN-EN trộn?

Dataset 20 câu TỔNG HỢP 100% fake PII tự sinh trong script (không data thật).
Recognizer set: builtin EMAIL/URL/IP + VN_PHONE + CCCD_12 tự viết + Stanza vi cho PERSON.
Pass: recall >= 80% với obvious types (email/phone/CCCD); PERSON = usable-with-caveat.
Fallback đo thêm: regex-only (bỏ NLP engine) để so sánh.
Output: JSON ra stdout + results/s1_presidio_vi_result.json (gitignored).
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import save_result, utf8_stdio  # noqa: E402

os.environ.setdefault("STANZA_RESOURCES_DIR", r"D:\stanza_resources")
utf8_stdio()

from presidio_analyzer import (  # noqa: E402
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.entity_recognizer import EntityRecognizer  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402
from presidio_analyzer.predefined_recognizers import (  # noqa: E402
    EmailRecognizer,
    IpRecognizer,
    UrlRecognizer,
)

# --- 20 mẫu tổng hợp, fake 100% (example.com / dải IP private / số tuần tự) ---
SAMPLES = [
    ("Đăng nhập bằng email nguyen.van.a@example.com không được, app báo lỗi liên tục.",
     [("EMAIL", "nguyen.van.a@example.com")]),
    ("Hotline 0901234567 gọi mãi không gặp ai hỗ trợ cả.",
     [("PHONE", "0901234567")]),
    ("Tôi là Nguyễn Văn A, tài khoản bị khoá không rõ lý do.",
     [("PERSON", "Nguyễn Văn A")]),
    ("Xem bài hướng dẫn tại https://example.com/bai-viet nhưng trang chết luôn.",
     [("URL", "https://example.com/bai-viet")]),
    ("Máy chủ 192.168.1.10 trả về lỗi 500 mỗi lần tôi upload file.",
     [("IP", "192.168.1.10")]),
    ("CCCD của tôi 012345678901 đã xác minh 3 ngày vẫn chưa xong.",
     [("CCCD", "012345678901")]),
    ("Liên hệ hotro247@spam.test để khiếu nại đơn hàng bị trễ.",
     [("EMAIL", "hotro247@spam.test")]),
    ("Số điện thoại người nhận là +84912345678, giao chậm quá.",
     [("PHONE", "+84912345678")]),
    ("Bạn Trần Thị B cũng bị lỗi tương tự khi thanh toán bằng thẻ.",
     [("PERSON", "Trần Thị B")]),
    ("Truy cập http://example.com/huong-dan để xem cách reset mật khẩu nhé.",
     [("URL", "http://example.com/huong-dan")]),
    ("IP 10.0.0.42 của phòng máy cứ bị chặn bởi firewall của app.",
     [("IP", "10.0.0.42")]),
    ("Ghi hộ tôi số CCCD 098765432109 vào hồ sơ bảo hành giúp.",
     [("CCCD", "098765432109")]),
    ("Phone number 0912 345 678 đổi rồi mà hệ thống vẫn gửi OTP về số cũ.",
     [("PHONE", "0912 345 678")]),
    ("Email le.thi.c@company.example bị trùng khi đăng ký tài khoản mới.",
     [("EMAIL", "le.thi.c@company.example")]),
    ("Anh Phạm Văn D bảo tính năng xuất báo cáo bị treo ở bước cuối.",
     [("PERSON", "Phạm Văn D")]),
    ("The webhook https://api.example.com/callback fails with timeout every night.",
     [("URL", "https://api.example.com/callback")]),
    ("Sim mới của tôi 0988 777 666 không nhận được mã xác thực.",
     [("PHONE", "0988 777 666")]),
    ("Vui lòng bỏ IP 172.16.0.99 ra khỏi danh sách đen giúp tôi.",
     [("IP", "172.16.0.99")]),
    ("Chị Võ Thị E khai CCCD 034567891234 nhưng hệ thống từ chối.",
     [("CCCD", "034567891234")]),
    ("Gửi phản hồi tới feedback@example.org thì bot auto-reply ngay.",
     [("EMAIL", "feedback@example.org")]),
]

TYPE_MAP = {
    "EMAIL": "EMAIL_ADDRESS",
    "PHONE": "VN_PHONE",
    "CCCD": "CCCD_12",
    "URL": "URL",
    "IP": "IP_ADDRESS",
    "PERSON": "PERSON",
}
OBVIOUS_TYPES = ["EMAIL", "PHONE", "CCCD"]

_STRIP_RE = re.compile(r"[\s.\-]+")


def norm(text):
    return _STRIP_RE.sub("", text).lower()


class VnPhoneRecognizer(PatternRecognizer):
    """VN mobile: (0|+84) theo đầu 3/5/7/8/9 + 8 số; space/dot được normalize trước match."""

    PATTERNS = [Pattern(name="vn_phone", regex=r"(?:\+84|0)(?:3|5|7|8|9)\d{8}", score=0.85)]

    def __init__(self):
        super().__init__(
            supported_entity="VN_PHONE",
            patterns=self.PATTERNS,
            supported_language="vi",
            name="VN Phone Recognizer",
        )


class CccdRecognizer(PatternRecognizer):
    PATTERNS = [Pattern(name="cccd_12", regex=r"\b\d{12}\b", score=0.9)]

    def __init__(self):
        super().__init__(
            supported_entity="CCCD_12",
            patterns=self.PATTERNS,
            supported_language="vi",
            name="VN CCCD Recognizer",
        )


class VnEmailRecognizer(PatternRecognizer):
    """Email pattern rộng hơn builtin: bắt cả TLD dự phòng (.test/.example)."""

    PATTERNS = [
        Pattern(
            name="vn_email",
            regex=r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
            score=0.9,
        )
    ]

    def __init__(self):
        super().__init__(
            supported_entity="EMAIL_ADDRESS",
            patterns=self.PATTERNS,
            supported_language="vi",
            name="VN Email Recognizer",
        )


class StanzaViPersonRecognizer(EntityRecognizer):
    """PERSON lấy thẳng từ nlp_artifacts của engine stanza vi.

    Workaround bug presidio-analyzer 2.2.364: StanzaRecognizer.__init__ forwarding
    kwarg `nlp_engine` lên SpacyRecognizer (không nhận) -> TypeError khi dựng trực
    tiếp, nên recognizer builtin vô dụng ngoài luồng AnalyzerEngine mặc định.
    """

    DEFAULT_EXPLANATION = "Vietnamese person name detected by stanza NER"

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language="vi",
            name="Stanza Vi PERSON",
        )

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=None):  # noqa: ARG002
        if nlp_artifacts is None or not nlp_artifacts.entities:
            return []
        results = []
        for ent in nlp_artifacts.entities:
            if ent.label_ != "PERSON" or not ent.text.strip():
                continue
            results.append(
                RecognizerResult(
                    entity_type="PERSON",
                    start=ent.start_char,
                    end=ent.end_char,
                    score=0.85,
                    recognition_metadata={
                        "model_name": "stanza-vi-vlsp",
                        "document_type": "feedback",
                    },
                )
            )
        return self.remove_duplicates(results)


_PHONE_SEP_RE = re.compile(r"(?<=[0-9])[ .\-](?=[0-9])")


def extra_phone_matches(text):
    """Số điện thoại có space/dot/dash giữa các chữ số: chạy VN_PHONE trên bản normalize."""
    stripped = _PHONE_SEP_RE.sub("", text)
    if stripped == text:
        return []
    recognizer = VnPhoneRecognizer()
    return [
        ("PHONE", stripped[r.start : r.end])
        for r in recognizer.analyze(text=stripped, entities=["VN_PHONE"], nlp_artifacts=None)
    ]


def build_analyzers():
    t0 = time.perf_counter()
    nlp_cfg = {"nlp_engine_name": "stanza", "models": [{"lang_code": "vi", "model_name": "vi"}]}
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_cfg).create_engine()

    registry_full = RecognizerRegistry(supported_languages=["vi"])
    for recognizer in (
        EmailRecognizer(supported_language="vi"),
        UrlRecognizer(supported_language="vi"),
        IpRecognizer(supported_language="vi"),
        VnEmailRecognizer(),
        VnPhoneRecognizer(),
        CccdRecognizer(),
        StanzaViPersonRecognizer(),
    ):
        registry_full.add_recognizer(recognizer)
    analyzer_full = AnalyzerEngine(
        nlp_engine=nlp_engine, registry=registry_full, supported_languages=["vi"]
    )
    return analyzer_full, time.perf_counter() - t0


REGEX_ONLY_RECOGNIZERS = (
    EmailRecognizer(supported_language="vi"),
    UrlRecognizer(supported_language="vi"),
    IpRecognizer(supported_language="vi"),
    VnEmailRecognizer(),
    VnPhoneRecognizer(),
    CccdRecognizer(),
)


def regex_only_recall(samples):
    """Regex-only KHÔNG qua AnalyzerEngine (nó bắt buộc có NLP engine mặc định).

    Gọi trực tiếp từng PatternRecognizer.analyze(nlp_artifacts=None) — vẫn là
    Presidio recognizer thật, chỉ bỏ tầng NLP.
    """
    per_type = {t: {"planted": 0, "hit": 0} for t in TYPE_MAP}
    misses = 0
    for text, planted in samples:
        detected = []
        for recognizer in REGEX_ONLY_RECOGNIZERS:
            entity_name = recognizer.supported_entities[0]
            results = recognizer.analyze(
                text=text, entities=[entity_name], nlp_artifacts=None
            )
            detected.extend(
                (r.entity_type, norm(text[r.start : r.end])) for r in results
            )
        for etype_extra, raw_val in extra_phone_matches(text):
            detected.append((TYPE_MAP[etype_extra], norm(raw_val)))
        for etype, value in planted:
            per_type[etype]["planted"] += 1
            target = norm(value)
            if any(
                det_type == TYPE_MAP[etype] and (target in det_val or det_val in target)
                for det_type, det_val in detected
            ):
                per_type[etype]["hit"] += 1
            else:
                misses += 1
    return per_type, misses


def recall_for(analyzer, samples):
    per_type = {t: {"planted": 0, "hit": 0} for t in TYPE_MAP}
    misses = []
    for text, planted in samples:
        entities = analyzer.analyze(text=text, language="vi")
        detected = [(e.entity_type, norm(text[e.start : e.end])) for e in entities]
        for etype_extra, raw_val in extra_phone_matches(text):
            detected.append((TYPE_MAP[etype_extra], norm(raw_val)))
        for etype, value in planted:
            per_type[etype]["planted"] += 1
            target = norm(value)
            hit = any(
                det_type == TYPE_MAP[etype]
                and (target in det_val or det_val in target)
                for det_type, det_val in detected
            )
            if hit:
                per_type[etype]["hit"] += 1
            else:
                misses.append({"type": etype})
    result = {}
    for etype, stats in per_type.items():
        recall = round(stats["hit"] / stats["planted"], 3) if stats["planted"] else None
        result[etype] = {**stats, "recall": recall}
    return result, len(misses)


def with_recalls(per_type, misses):
    """Cùng hình dạng output với recall_for nhưng nhận sẵn thống kê đếm."""
    result = {}
    for etype, stats in per_type.items():
        recall = round(stats["hit"] / stats["planted"], 3) if stats["planted"] else None
        result[etype] = {**stats, "recall": recall}
    return result, misses


def main():
    t_start = time.perf_counter()
    analyzer_full, load_seconds = build_analyzers()

    full_recall, full_misses = recall_for(analyzer_full, SAMPLES)
    regex_recall, regex_misses = with_recalls(*regex_only_recall(SAMPLES))

    def obvious(recall_map):
        vals = [recall_map[t]["recall"] for t in OBVIOUS_TYPES]
        return all(v is not None and v >= 0.8 for v in vals)

    pass_full = obvious(full_recall)
    report = {
        "spike": "S1",
        "n_samples": len(SAMPLES),
        "engine_load_seconds": round(load_seconds, 1),
        "full_mode": {
            "per_type": full_recall,
            "misses_total": full_misses,
            "obvious_ge_80pct": pass_full,
        },
        "regex_only_mode": {
            "per_type": regex_recall,
            "misses_total": regex_misses,
            "obvious_ge_80pct": obvious(regex_recall),
        },
        "person_note": (
            "PERSON đánh giá usable-with-caveat — precision/recall của NER tiếng Việt "
            "thấp hơn pattern types là chấp nhận được theo plan §3.1."
        ),
        "notes": {
            "custom_recognizers": [
                "VnEmailRecognizer - builtin email regex bo sot TLD du phong (.test/.example)",
                "VnPhoneRecognizer + normalize khoang cach/dot giua chu so",
                "CccdRecognizer (regex 12 so)",
                "StanzaViPersonRecognizer - workaround bug presidio-analyzer 2.2.364"
                " (StanzaRecognizer.__init__ TypeError khi truyen nlp_engine)",
            ],
            "known_overlap": (
                "CCCD 12 so co the overlap VN_PHONE 10 so con - Phase 06 can rule uu tien CCCD"
            ),
        },
        "pass": pass_full,
        "production_mode": "presidio_full" if pass_full else "regex_only_fallback_measured",
        "total_seconds": round(time.perf_counter() - t_start, 1),
    }
    save_result("s1_presidio_vi", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
