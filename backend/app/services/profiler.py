"""Column Profiler — DETERMINISTIC, KHÔNG LLM (VoC OS §7, plan 22 Task 2).

Chỉ PROFILE đi vào LLM mapper — không bao giờ gửi toàn bộ CSV (guardrail §69).
Type detection theo thứ tự thử: boolean → numeric → datetime → category
(cardinality thấp) → text.
"""

import io
from collections.abc import Iterable
from datetime import datetime

_SAMPLES = 5
_CATEGORY_MAX_CARDINALITY = 25
_MAX_COLUMNS = 200


def _parse_number(value: str) -> float | None:
    try:
        return float(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def _is_integer_like(value: str) -> bool:
    """Chuỗi số NGUYÊN (không dấu chấm thập phân) — '3' integer, '2.17' không."""
    v = value.replace(",", "").strip()
    return v.lstrip("+-").isdigit()


def _has_fraction(value: str) -> bool:
    """Có phần thập phân thật ('2.17' → True; '3', '10' → False)."""
    return "." in value.replace(",", "").strip()


def _detect_type(values: list[str], unique: set[str]) -> str:
    """Infer detected_type từ sample non-empty values (đã strip).

    Heuristic version-identifier: TẤT CẢ giá trị số-có-thập-phân và
    cardinality thấp (vd '2.17', '2.16' — version build) → CATEGORY, vì
    version là chiều phân tích rời rạc (VoC OS §7 example). Trộn integer +
    decimal (vd '1', '2.5') → numeric thường.
    """
    non_empty = [v for v in values if v]
    if not non_empty:
        return "text"
    if len(unique) <= 2 and all(v.lower() in {"true", "false", "yes", "no", "0", "1"} for v in non_empty):
        return "boolean"
    all_numeric = all(_parse_number(v) is not None for v in non_empty)
    if all_numeric:
        if all(_is_integer_like(v) for v in non_empty):
            return "numeric"
        if all(_has_fraction(v) for v in non_empty) and len(unique) <= _CATEGORY_MAX_CARDINALITY:
            return "category"
        return "numeric"
    if all(_parse_datetime(v) is not None for v in non_empty):
        return "datetime"
    if len(unique) <= _CATEGORY_MAX_CARDINALITY:
        return "category"
    return "text"


def profile_columns(rows: Iterable[dict]) -> list[dict]:
    """Profile DETERMINISTIC từng cột từ list dict (đã parse CSV).

    Mỗi cột: name, detected_type, missing_rate, unique_count, cardinality,
    sample_values ≤5, min/max (numeric/datetime — ISO string), avg_length.
    Giới hạn _MAX_COLUMNS chống CSV dị dạng.
    """
    columns: dict[str, list[str]] = {}
    for row in rows:
        for key, value in row.items():
            if key not in columns:
                columns[key] = []
            if len(columns[key]) < 500:  # cap bộ nhớ: sample đủ cho profile
                columns[key].append("" if value is None else str(value))
            elif key in columns:
                # vẫn đếm missing qua empty string nhưng bỏ qua value dài
                columns[key].append(value if value in (None, "") else "")

    profiles: list[dict] = []
    for name, values in list(columns.items())[:_MAX_COLUMNS]:
        non_empty = [v.strip() for v in values if v is not None and str(v).strip() != ""]
        unique = set(non_empty)
        detected = _detect_type(non_empty, unique)
        # sample dedup giữ thứ tự (§7 example: samples là các giá trị phân biệt)
        seen: set[str] = set()
        samples = [v for v in non_empty if not (v in seen or seen.add(v))][:_SAMPLES]
        profile: dict = {
            "name": name,
            "detected_type": detected,
            "missing_rate": round((len(values) - len(non_empty)) / len(values), 4) if values else 1.0,
            "unique_count": len(unique),
            "cardinality": len(unique),
            "sample_values": samples,
            "avg_length": round(sum(len(v) for v in non_empty) / len(non_empty), 1) if non_empty else 0,
        }
        if detected == "numeric":
            numbers = [n for v in non_empty if (n := _parse_number(v)) is not None]
            if numbers:
                profile["min"] = min(numbers)
                profile["max"] = max(numbers)
        elif detected == "datetime":
            dts = [d for v in non_empty if (d := _parse_datetime(v)) is not None]
            if dts:
                profile["min"] = min(dts).isoformat()
                profile["max"] = max(dts).isoformat()
        profiles.append(profile)
    return profiles


def profile_csv_bytes(raw: bytes) -> list[dict]:
    """Convenience: bytes CSV → profiles (utf-8-sig chống BOM Excel)."""
    text = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8-sig", newline="")
    import csv

    return profile_columns(csv.DictReader(text))
