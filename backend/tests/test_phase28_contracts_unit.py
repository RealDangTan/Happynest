"""Public schema contracts for controlled imports and scoped analysis."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.import_ import ImportOut


def test_import_out_accepts_profile_ready_activity_shape():
    body = ImportOut.model_validate(
        {
            "id": uuid.uuid4(),
            "product_id": uuid.uuid4(),
            "source_type": "csv",
            "storage_path": "storage/imports/file.csv",
            "original_filename": "feedback.csv",
            "mapping_version": None,
            "schema_version": None,
            "status": "profile_ready",
            "row_count": None,
            "source_row_count": 42,
            "column_profiles": [{"name": "message", "sample_values": ["safe"]}],
            "report": None,
            "mapping_started_at": None,
            "error": None,
            "created_at": datetime.now(timezone.utc),
        }
    )

    assert body.status.value == "profile_ready"
    assert body.original_filename == "feedback.csv"
    assert body.source_row_count == 42


def test_analysis_scope_requires_ids_only_for_selected_mode():
    from app.schemas.analysis import AnalysisScopeIn

    import_id = uuid.uuid4()
    feedback_id = uuid.uuid4()
    selected = AnalysisScopeIn.model_validate(
        {"mode": "selected", "import_id": import_id, "feedback_ids": [feedback_id]}
    )
    assert selected.feedback_ids == [feedback_id]

    batch = AnalysisScopeIn.model_validate({"mode": "batch", "import_id": import_id})
    assert batch.feedback_ids is None

    with pytest.raises(ValidationError):
        AnalysisScopeIn.model_validate({"mode": "selected", "import_id": import_id})
    with pytest.raises(ValidationError):
        AnalysisScopeIn.model_validate(
            {"mode": "batch", "import_id": import_id, "feedback_ids": [feedback_id]}
        )
