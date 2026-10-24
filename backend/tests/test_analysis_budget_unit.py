import uuid

import pytest
from pydantic import ValidationError

from app.schemas.analysis import AnalysisScopeIn
from app.services.analysis_service import build_cost_receipt


def test_batch_receipt_counts_one_pair_per_item_singular() -> None:
    """v4 singular (owner 2026-10-22): mọi mode — mỗi item 1 enrich + 1 embed."""
    receipt = build_cost_receipt(
        mode="batch",
        texts=["abc" for _ in range(23)],
        eligible_count=40,
        chunk_size=1,
    )

    assert receipt.selected_count == 23
    assert receipt.remaining_count == 17
    assert receipt.logical_classify_requests == 23
    assert receipt.logical_embedding_requests == 23
    assert receipt.max_provider_attempts == 23 * 7
    assert receipt.chunk_size == 1


def test_selected_receipt_uses_one_logical_pair_per_item() -> None:
    receipt = build_cost_receipt(
        mode="selected",
        texts=["one", "two"],
        eligible_count=8,
        chunk_size=1,
    )

    assert receipt.logical_classify_requests == 2
    assert receipt.logical_embedding_requests == 2
    assert receipt.max_provider_attempts == 14
    assert receipt.remaining_count == 6


def test_selected_scope_rejects_duplicate_ids() -> None:
    item_id = uuid.uuid4()
    with pytest.raises(ValidationError, match="duplicate"):
        AnalysisScopeIn(
            mode="selected",
            import_id=uuid.uuid4(),
            feedback_ids=[item_id, item_id],
        )
