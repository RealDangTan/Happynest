"""Unit tests insight engine — Phase 15 Tasks 1–2 (plan 15).

Chiến lược DB theo conftest Phase 11: mọi INSERT đi qua fixture `db_session`
(ROLLBACK khi test xong) — không row `ins-it-` nào bám lại DB dev dùng chung.
LLM mock HOÀN TOÀN qua monkeypatch `chat_structured` — suite xanh offline,
không đốt tín dụng.
"""

from uuid import uuid4

import pytest

from tests.conftest import _SKIP_MSG, db_reachable


# ------------------------------------------------------------------ Task 1 cap


class TestInsightMaxClustersSetting:
    """Step 1.2 — default + env override, đọc độc lập .env người dùng."""

    def _settings(self) -> type:
        from app.core.config import Settings

        return Settings(_env_file=None, DATABASE_URL="postgresql+psycopg://t:t@h/db")

    def test_default_is_10(self, monkeypatch) -> None:
        monkeypatch.delenv("INSIGHT_MAX_CLUSTERS", raising=False)
        assert self._settings().INSIGHT_MAX_CLUSTERS == 10

    def test_env_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("INSIGHT_MAX_CLUSTERS", "3")
        assert self._settings().INSIGHT_MAX_CLUSTERS == 3
