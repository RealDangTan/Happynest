"""Presidio PII sanitization — Phase 06 (06-pii-presidio-service.md §3.1).

⚠️ RANH GIỚI PII (hard rule #2): output của hàm `sanitize()` là thứ DUY NHẤT
được phép đi tiếp vào LLM / log / trace / API mặc định. `raw_content` không
bao giờ rời biên sanitize. `entities` trong kết quả chỉ chứa METADATA
{type, start, end, score} — tuyệt đối KHÔNG chứa chuỗi raw (cột jsonb
`pii_entities` có thể bị đọc qua API).

Kiến trúc: AnalyzerEngine + StanzaNlpEngine (vi+en) khởi tạo ĐÚNG MỘT LẦN
(`init_presidio()` được lifespan gọi; `sanitize()` tự lazy-init cho CLI/test).
Nếu Stanza lỗi init trên Windows → tự rơi về chế độ regex-only (mất PERSON,
các obvious type vẫn đủ ≥80% recall theo đo S1) — sự kiện này BẮT BUỘC entry
decisions.md.

Recognizer set theo S1 đã PASS trên máy dev (scripts/spikes/s1_presidio_vi.py):
builtin Email/Url/Ip + custom VnEmail (rộng hơn builtin, bắt TLD dự phòng),
VnPhone (nhận cả dạng có space/dot/dash giữa chữ số nhờ lookaround),
Cccd 12 số, PERSON từ NER stanza (workaround bug presidio-analyzer 2.2.364:
StanzaRecognizer dựng trực tiếp bị TypeError nên tự viết recognizer đọc
nlp_artifacts). Lookaround `(?<!\\d)…(?!\\d)` giải luôn chồng lấn CCCD ⊃ PHONE
ghi chú trong S1: phone không khớp bên trong chuỗi 12 số.
"""

import os
import re
import threading

from pydantic import BaseModel, Field
from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.entity_recognizer import EntityRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    EmailRecognizer,
    IpRecognizer,
    UrlRecognizer,
)
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Spike S1 đặt env trước khi stanza import — giữ nguyên để test/CLI chạy được
# dù biến môi trường hệ thống chưa có.
os.environ.setdefault("STANZA_RESOURCES_DIR", r"D:\stanza_resources")

# Regex VN_PHONE của plan + lookaround chống khớp trong dãy số dài hơn
# (CCCD 12 số, OTP 11 số…): prefix 0|+84, đầu số 3/5/7/8/9, tổng 9 số sau,
# chấp nhận space/dot/dash giữa các chữ số ("0912 345 678").
_VN_PHONE_REGEX = r"(?<!\d)(?:\+84|0)[ .-]?(?:3|5|7|8|9)(?:[ .-]?\d){8}(?!\d)"
_CCCD_REGEX = r"\b\d{12}\b"
_EMAIL_REGEX = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"

# Mapping hiển thị placeholder — tên loại đích KHÁC tên entity (VN_PHONE→
# <PHONE_NUMBER>, CCCD_12→<CCCD>). DEFAULT là lưới an toàn: loại lạ nào bị
# detect cũng bị mask thay vì lộ ra ngoài biên.
_PLACEHOLDERS = {
    "EMAIL_ADDRESS": "<EMAIL>",
    "PHONE_NUMBER": "<PHONE_NUMBER>",
    "VN_PHONE": "<PHONE_NUMBER>",
    "URL": "<URL>",
    "IP_ADDRESS": "<IP_ADDRESS>",
    "CCCD_12": "<CCCD>",
    "PERSON": "<PERSON>",
}

_LANG = "vi"  # mọi analyze chạy dưới bucket 'vi'; EN trộn được xử lý bởi regex


class PiiEntity(BaseModel):
    """Metadata-only — cấm thêm trường mang text raw."""

    type: str
    start: int
    end: int
    score: float


class SanitizeResult(BaseModel):
    sanitized_text: str
    pii_detected: bool
    entities: list[PiiEntity] = Field(default_factory=list)


class _VnEmailRecognizer(PatternRecognizer):
    """Email rộng hơn builtin: bắt cả TLD dự phòng (.test/.example) — S1."""

    PATTERNS = [Pattern(name="vn_email", regex=_EMAIL_REGEX, score=0.9)]

    def __init__(self):
        super().__init__(
            supported_entity="EMAIL_ADDRESS",
            patterns=self.PATTERNS,
            supported_language=_LANG,
            name="VN Email Recognizer",
        )


class _VnPhoneRecognizer(PatternRecognizer):
    PATTERNS = [Pattern(name="vn_phone", regex=_VN_PHONE_REGEX, score=0.85)]

    def __init__(self):
        super().__init__(
            supported_entity="VN_PHONE",
            patterns=self.PATTERNS,
            supported_language=_LANG,
            name="VN Phone Recognizer",
        )


class _CccdRecognizer(PatternRecognizer):
    PATTERNS = [Pattern(name="cccd_12", regex=_CCCD_REGEX, score=0.9)]

    def __init__(self):
        super().__init__(
            supported_entity="CCCD_12",
            patterns=self.PATTERNS,
            supported_language=_LANG,
            name="VN CCCD Recognizer",
        )


class _StanzaPersonRecognizer(EntityRecognizer):
    """PERSON từ nlp_artifacts của engine stanza — workaround bug presidio
    2.2.364 (xem docstring module). Score cố định thấp-trung bình: NER tiếng
    Việt yếu hơn pattern types, chấp nhận caveat theo S1."""

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language=_LANG,
            name="Stanza Vi PERSON",
        )

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=None):  # noqa: ARG002
        if nlp_artifacts is None or not nlp_artifacts.entities:
            return []
        results = [
            RecognizerResult(
                entity_type="PERSON",
                start=ent.start_char,
                end=ent.end_char,
                score=0.85,
                recognition_metadata={"model_name": "stanza-vi"},
            )
            for ent in nlp_artifacts.entities
            if ent.label_ == "PERSON" and ent.text.strip()
        ]
        return self.remove_duplicates(results)


# --- Singleton state -------------------------------------------------------
_init_lock = threading.Lock()
_analyzer: AnalyzerEngine | None = None
_pattern_recognizers: tuple[PatternRecognizer, ...] | None = None
_anonymizer: AnonymizerEngine | None = None
_anonymizer_operators: dict | None = None
_nlp_failed_reason: str | None = None


def _build_nlp_engine():
    cfg = {
        "nlp_engine_name": "stanza",
        "models": [
            {"lang_code": "vi", "model_name": "vi"},
            {"lang_code": "en", "model_name": "en"},
        ],
    }
    return NlpEngineProvider(nlp_configuration=cfg).create_engine()


def init_presidio() -> None:
    """Khởi tạo analyzer/anonymizer MỘT LẦN (lifespan gọi; idempotent, thread-safe).

    Stanza init fail → regex-only fallback: `_analyzer` giữ None, sanitize chạy
    trực tiếp các PatternRecognizer (vẫn Presidio thật, chỉ bỏ tầng NLP/PERSON).
    """
    global _analyzer, _pattern_recognizers, _anonymizer, _anonymizer_operators
    global _nlp_failed_reason
    with _init_lock:
        if _anonymizer is not None:
            return
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        _pattern_recognizers = (
            EmailRecognizer(supported_language=_LANG),
            UrlRecognizer(supported_language=_LANG),
            IpRecognizer(supported_language=_LANG),
            _VnEmailRecognizer(),
            _VnPhoneRecognizer(),
            _CccdRecognizer(),
        )
        try:
            nlp_engine = _build_nlp_engine()
            registry = RecognizerRegistry(supported_languages=[_LANG])
            for recognizer in (*_pattern_recognizers, _StanzaPersonRecognizer()):
                registry.add_recognizer(recognizer)
            _analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine, registry=registry, supported_languages=[_LANG]
            )
        except Exception as exc:  # noqa: BLE001 — fallback có chủ đích
            _nlp_failed_reason = f"{type(exc).__name__}: {exc}"
            logger.error(
                "presidio: Stanza init FAILED — fallback regex-only (mất PERSON): %s",
                _nlp_failed_reason,
            )
        _anonymizer = AnonymizerEngine()
        _anonymizer_operators = {
            etype: OperatorConfig("replace", {"new_value": ph})
            for etype, ph in _PLACEHOLDERS.items()
        }
        # Lưới an toàn: loại lạ nào bị detect cũng bị mask thay vì lộ ra ngoài biên.
        _anonymizer_operators["DEFAULT"] = OperatorConfig(
            "replace", {"new_value": "<PII>"}
        )


def _anonymize(text: str, results: list[RecognizerResult]) -> str:
    if not results:
        return text
    return _anonymizer.anonymize(
        text=text, analyzer_results=results, operators=_anonymizer_operators
    ).text


def _analyze_regex_only(text: str) -> list[RecognizerResult]:
    found: list[RecognizerResult] = []
    for recognizer in _pattern_recognizers or ():
        for entity_name in recognizer.supported_entities:
            found.extend(
                recognizer.analyze(text=text, entities=[entity_name], nlp_artifacts=None)
            )
    return found


def _to_metadata(results: list[RecognizerResult]) -> list[PiiEntity]:
    return sorted(
        (
            PiiEntity(type=r.entity_type, start=r.start, end=r.end, score=r.score)
            for r in results
        ),
        key=(lambda e: (e.start, e.end)),
    )


def mode() -> dict:
    """Trạng thái hiện tại — phục vụ health/debug; KHÔNG chứa dữ liệu."""
    return {
        "initialized": _anonymizer is not None,
        "mode": "full" if (_anonymizer is not None and _analyzer is not None)
        else ("regex_only" if _anonymizer is not None else "uninitialized"),
        "nlp_failed_reason": _nlp_failed_reason,
    }


def sanitize(raw: str) -> SanitizeResult:
    """Sanitize 1 chuỗi raw → (sanitized_text, pii_detected, entities metadata).

    Lazy-init nếu chưa (CLI/backfill/test không cần qua app startup).
    """
    if _anonymizer is None:
        init_presidio()

    if _analyzer is not None:
        results = _analyzer.analyze(text=raw, language=_LANG)
    else:
        results = _analyze_regex_only(raw)

    sanitized = _anonymize(raw, list(results))
    metadata = _to_metadata(list(results))
    return SanitizeResult(
        sanitized_text=sanitized,
        pii_detected=bool(metadata),
        entities=metadata,
    )
