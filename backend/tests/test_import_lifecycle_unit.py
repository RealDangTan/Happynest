from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.enums import ImportStatus
from app.services.import_service import begin_mapping_proposal, cancel_import_file


class _Db:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def test_mapping_proposal_claims_profile_ready_import() -> None:
    now = datetime(2026, 8, 30, tzinfo=UTC)
    row = SimpleNamespace(
        status=ImportStatus.profile_ready,
        mapping_started_at=None,
        error=None,
    )
    db = _Db()

    begin_mapping_proposal(db, row, now=now)

    assert row.status == ImportStatus.mapping_generating
    assert row.mapping_started_at == now
    assert row.error is None
    assert db.commits == 1


def test_mapping_proposal_reclaims_only_after_five_minutes() -> None:
    now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    row = SimpleNamespace(
        status=ImportStatus.mapping_generating,
        mapping_started_at=now - timedelta(minutes=4, seconds=59),
        error=None,
    )

    with pytest.raises(ValueError, match="mapping_generating"):
        begin_mapping_proposal(_Db(), row, now=now)

    row.mapping_started_at = now - timedelta(minutes=5, seconds=1)
    db = _Db()
    begin_mapping_proposal(db, row, now=now)

    assert row.mapping_started_at == now
    assert db.commits == 1


def test_cancel_import_deletes_only_file_inside_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "imports"
    storage_root.mkdir()
    raw_file = storage_root / "safe.csv"
    raw_file.write_text("content\nhello", encoding="utf-8")
    row = SimpleNamespace(
        status=ImportStatus.mapping_review,
        storage_path=str(raw_file),
    )

    cancel_import_file(row, storage_root=storage_root)

    assert not raw_file.exists()
    assert row.storage_path is None
    assert row.status == ImportStatus.cancelled


def test_cancel_import_rejects_path_outside_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "imports"
    storage_root.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("secret", encoding="utf-8")
    row = SimpleNamespace(
        status=ImportStatus.profile_ready,
        storage_path=str(outside),
    )

    with pytest.raises(ValueError, match="storage root"):
        cancel_import_file(row, storage_root=storage_root)

    assert outside.exists()
