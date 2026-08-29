"""Import orchestration — LISTEN pipeline (VoC OS §6, plan 22 Task 4).

Flow: POST /imports (upload) → save raw (disk — decisions 2026-08-28) →
deterministic profile → LLM mapper proposal → status=mapping_review →
Gate #1 human decision → validate → activate candidate schema version →
parse + sanitize + insert feedback rows → status=imported.

PII boundary: raw file nằm ngoài DB; chỉ `feedback_text` (sanitize) đi vào
pipeline. LLM mapper chỉ thấy PROFILE, không thấy data raw (VoC OS §7).
"""

import csv
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import ImportStatus
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.schemas.import_ import (
    MappingDecisionItem,
    MappingItemOut,
    MappingProposalOut,
)
from app.services import schema_registry
from app.services.llm_mapper import build_mapping_proposal
from app.services.presidio_service import sanitize
from app.services.profiler import profile_csv_bytes


class ImportStateError(Exception):
    """Import không ở trạng thái mapping_review — route chuyển 409."""


# ------------------------------------------------------------------ storage


def _storage_dir() -> Path:
    path = Path(get_settings().IMPORT_STORAGE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_raw_import(raw: bytes, import_id: uuid.UUID) -> str:
    """Lưu raw file ngoài DB (§18 — local disk theo decisions 2026-08-28)."""
    path = _storage_dir() / f"{import_id}.csv"
    path.write_bytes(raw)
    return str(path)


def load_raw_import(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()


# ------------------------------------------------------------- proposal


def start_import(db: Session, product_id: uuid.UUID, raw: bytes) -> Import:
    """Upload → profile → LLM map → chờ Gate #1. LLM fail → import failed.

    409-equivalent: product đang có import dở mapping_review → ImportStateError
    (route chuyển 409) — tránh 2 proposal chồng chéo trên cùng schema.
    """
    in_review = (
        db.query(Import.id)
        .filter(
            Import.product_id == product_id,
            Import.status == ImportStatus.mapping_review,
        )
        .first()
    )
    if in_review is not None:
        raise ImportStateError(
            "Product đang có import chờ review mapping. Hoàn tất Gate #1 trước."
        )

    import_row = Import(
        product_id=product_id, source_type="csv", status=ImportStatus.pending
    )
    db.add(import_row)
    db.commit()
    db.refresh(import_row)

    import_row.storage_path = save_raw_import(raw, import_row.id)

    try:
        profiles = profile_csv_bytes(raw)
        schema = schema_registry.get_active_schema(db, product_id)
        existing = schema_registry.core_fields_for_llm() + schema_registry.schema_fields(schema)
        proposal = build_mapping_proposal(existing, profiles)
        import_row.mapping_proposal = proposal.model_dump()
        import_row.status = ImportStatus.mapping_review
        db.commit()
    except Exception as exc:
        import_row.status = ImportStatus.failed
        import_row.error = f"{type(exc).__name__}: {exc}"[:2000]
        db.commit()
        raise
    db.refresh(import_row)
    return import_row


def get_proposal(import_row: Import) -> MappingProposalOut:
    if import_row.mapping_proposal is None:
        raise ImportStateError("Import chưa có proposal mapping.")
    return MappingProposalOut.model_validate(import_row.mapping_proposal)


# ------------------------------------------------------------- Gate #1 apply


def _resolve_effective(
    db: Session,
    product_id: uuid.UUID,
    proposal: MappingProposalOut,
    decisions: list[MappingDecisionItem],
) -> tuple[dict[str, str], dict[str, dict]]:
    """Chốt mapping cuối per source_field từ (proposal + human override).

    Returns:
        final_map: {source_field: target_key} cho các cột MAP (core hoặc
                   product field) — product field CÓ THỂ là field mới promote.
        meta_fields: {source_field: None} cho SOURCE_META.
    """
    active = schema_registry.get_active_schema(db, product_id)
    known_keys = schema_registry.CORE_KEYS | {
        f["key"] for f in schema_registry.schema_fields(active)
    }
    new_fields: dict[str, dict] = {}
    final_map: dict[str, str] = {}
    meta_fields: set[str] = set()

    proposal_fields = {m.source_field for m in proposal.mappings}
    decided_fields = {d.source_field for d in decisions}
    if proposal_fields != decided_fields:
        raise ValueError(
            "decision phải phủ đúng các source_field của proposal: "
            f"thiếu {sorted(proposal_fields - decided_fields)}, "
            f"lạ {sorted(decided_fields - proposal_fields)}"
        )

    by_field = {m.source_field: m for m in proposal.mappings}
    for d in decisions:
        p = by_field[d.source_field]
        action = d.action
        if action == "approve":
            if p.decision == "MAP" and p.target:
                final_map[d.source_field] = p.target
            elif p.decision == "PROMOTE" and p.candidate:
                new_fields[p.candidate.key] = p.candidate.model_dump()
                final_map[d.source_field] = p.candidate.key
            elif p.decision == "SOURCE_META":
                meta_fields.add(d.source_field)
            elif p.decision == "IGNORE":
                pass
            else:  # AMBIGUOUS không được approve máy móc
                raise ValueError(
                    f"'{d.source_field}' AMBIGUOUS — human phải remap/promote/demote/ignore."
                )
        elif action == "remap":
            if not d.target_key:
                raise ValueError(f"remap '{d.source_field}' thiếu target_key.")
            if d.target_key not in known_keys:
                raise ValueError(
                    f"target_key '{d.target_key}' không có trong schema hiện có."
                )
            final_map[d.source_field] = d.target_key
        elif action == "promote":
            if d.candidate is None:
                raise ValueError(f"promote '{d.source_field}' thiếu candidate.")
            new_fields[d.candidate.key] = d.candidate.model_dump()
            final_map[d.source_field] = d.candidate.key
        elif action == "demote":
            meta_fields.add(d.source_field)
        elif action == "ignore":
            pass
        else:  # phòng thủ — schema chặn
            raise ValueError(f"action không hợp lệ: {action!r}")

    # 1 target chỉ nhận 1 cột — đè nghĩa lịch sử là điều cấm (§11)
    targets = list(final_map.values())
    if len(targets) != len(set(targets)):
        raise ValueError("Hai cột cùng MAP vào một target — không cho phép.")

    if "feedback_text" not in final_map.values():
        raise ValueError("Mapping phải có ít nhất 1 cột MAP vào feedback_text.")

    # Promote/new candidate → version mới (human đã duyệt qua Gate #1)
    if new_fields:
        definition = {
            "fields": schema_registry.schema_fields(active)
            + [new_fields[k] for k in sorted(new_fields)]
        }
        schema_registry.create_active_version(db, product_id, definition)

    return final_map, {k: None for k in meta_fields}


def apply_mapping_decision(
    db: Session,
    import_row: Import,
    decisions: list[MappingDecisionItem],
    *,
    default_source: str | None = None,
    reviewer_id=None,
) -> dict:
    """Gate #1: chốt mapping → (tùy) activate schema version mới → import rows.

    Per-row error không abort file (precedent Phase 05); raw PII sanitize tại
    ingest. Trả report {imported, failed, errors, schema_version}.
    """
    if import_row.status != ImportStatus.mapping_review:
        raise ImportStateError(
            f"Import đang ở status '{import_row.status.value}' — không áp mapping được."
        )
    proposal = get_proposal(import_row)
    final_map, meta_fields = _resolve_effective(db, import_row.product_id, proposal, decisions)

    active = schema_registry.get_active_schema(db, import_row.product_id)
    product_field_keys = {
        t for t in final_map.values() if t not in schema_registry.CORE_KEYS
    }

    raw = load_raw_import(import_row.storage_path)
    reader = csv.DictReader(
        io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8-sig", newline="")
    )

    imported = 0
    errors: list[dict] = []
    for offset, row in enumerate(reader, start=2):
        # source_field → value (strip; DictReader trả None cho dòng ngắn)
        # — phủ CẢ meta_fields vì demote/SOURCE_META không nằm trong final_map.
        mapped_sources = set(final_map) | set(meta_fields)
        values = {
            src: ("" if row.get(src) is None else str(row[src]).strip())
            for src in mapped_sources
        }

        text_col = next(
            (s for s, t in final_map.items() if t == "feedback_text"), None
        )
        content = values.get(text_col, "")
        if not content:
            errors.append({"row": offset, "reason": "Cột feedback_text rỗng/thiếu."})
            continue

        occurred_at: datetime | None = None
        occurred_col = next(
            (s for s, t in final_map.items() if t == "occurred_at"), None
        )
        if occurred_col and values.get(occurred_col):
            try:
                occurred_at = datetime.fromisoformat(values[occurred_col])
            except ValueError:
                errors.append(
                    {"row": offset, "reason": f"occurred_at sai ISO 8601: {values[occurred_col]!r}"}
                )
                continue

        source_col = next((s for s, t in final_map.items() if t == "source"), None)
        source = (
            values.get(source_col) if source_col and values.get(source_col) else None
        ) or default_source or import_row.source_type

        record_id_col = next(
            (s for s, t in final_map.items() if t == "source_record_id"), None
        )

        data = {
            t: values[s]
            for s, t in final_map.items()
            if t in product_field_keys and values[s] != ""
        }
        source_meta = {s: values[s] for s in meta_fields if values[s] != ""}

        result = sanitize(content)
        db.add(
            Feedback(
                product_id=import_row.product_id,
                import_id=import_row.id,
                source=source[:100],
                source_record_id=(
                    values.get(record_id_col) or None
                )
                if record_id_col
                else None,
                occurred_at=occurred_at or datetime.now(timezone.utc),
                raw_content=content,
                feedback_text=result.sanitized_text,
                pii_detected=result.pii_detected,
                pii_entities=[e.model_dump() for e in result.entities],
                data=data,
                source_meta=source_meta,
            )
        )
        imported += 1

    import_row.row_count = imported
    import_row.status = ImportStatus.imported
    db.commit()

    # Decision memory (§52–53, plan 27): log Gate #1 — agent proposal vs human
    try:
        from app.models.enums import DecisionSubject
        from app.services.decision_log import log_decision

        log_decision(
            db,
            product_id=import_row.product_id,
            subject_type=DecisionSubject.schema_mapping,
            subject_id=import_row.id,
            agent_value=proposal.model_dump(),
            human_value={"decisions": [d.model_dump() for d in decisions]},
            reviewer_id=reviewer_id,
        )
    except Exception:  # noqa: BLE001 — memory không được phá flow
        db.rollback()

    return {
        "imported": imported,
        "failed": len(errors),
        "errors": errors,
        "schema_version": active.version if active else None,
        "import_id": import_row.id,
    }
