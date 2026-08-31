"""Offline contracts for Phase 28 controlled import staging."""

from types import SimpleNamespace

from app.services import import_service


def test_profile_preview_sanitizes_samples_before_storage(monkeypatch):
    """Raw sample values must never cross the persisted/prompt profile boundary."""

    def fake_sanitize(value: str):
        return SimpleNamespace(
            sanitized_text=value.replace("alice@example.com", "<EMAIL>"),
            pii_detected="@" in value,
            entities=[],
        )

    monkeypatch.setattr(import_service, "sanitize", fake_sanitize)
    raw = (
        b"message,email\n"
        b"App crashes,alice@example.com\n"
        b"Search is slow,bob@example.com\n"
    )

    profiles, source_row_count = import_service.profile_csv_for_import(raw)

    assert source_row_count == 2
    email_profile = next(p for p in profiles if p["name"] == "email")
    assert email_profile["sample_values"] == ["<EMAIL>", "bob@example.com"]
    assert "alice@example.com" not in str(profiles)


def test_profile_preview_rejects_empty_csv():
    try:
        import_service.profile_csv_for_import(b"message\n")
    except ValueError as exc:
        assert str(exc) == "CSV không có dòng dữ liệu."
    else:  # pragma: no cover - explicit failure message is clearer than pytest.raises here
        raise AssertionError("empty CSV must be rejected")
