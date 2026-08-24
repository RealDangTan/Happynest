"""Unit test embedder — FakeOpenAI, KHÔNG network, KHÔNG DB thật.

Phủ checklist plan 08 §3.4:
- batch split đúng (≤ EMBED_BATCH_MAX_INPUTS/call);
- thứ tự kết quả giữ nguyên dù fake trả .data ngược;
- dims sai → EmbeddingDimError;
- mỗi call ghi 1 row llm_call_logs (fake session recorder).
Retry tenacity không test ở đây (timing) — được cấu hình khai trong embedder.py.
"""

from types import SimpleNamespace

import pytest

from app.services import embedder
from app.services.embedder import (
    EMBED_BATCH_MAX_INPUTS,
    EmbeddingDimError,
    embed_one,
    embed_texts,
    store_embedding,
)

DIM = 3  # monkeypatch settings.EMBEDDING_DIM về 3 để vector tay ngắn gọn


class FakeUsage(SimpleNamespace):
    pass


class FakeData(SimpleNamespace):
    index: int
    embedding: list[float]


class _FakeSession:
    """Recorder thay SQLAlchemy session — bắt row LlmCallLog được add."""

    def __init__(self, bucket: list):
        self._bucket = bucket
        self.committed = False

    def add(self, row):
        self._bucket.append(row)

    def commit(self):
        self.committed = True


class _FakeSessionFactory:
    def __init__(self, bucket: list):
        self.bucket = bucket
        self.sessions: list[_FakeSession] = []

    def __call__(self):
        s = _FakeSession(self.bucket)
        self.sessions.append(s)
        return self  # __enter__ trả session thật

    def __enter__(self):
        return self.current

    def __exit__(self, *exc):
        return False

    @property
    def current(self):
        if not self.sessions:
            raise RuntimeError("session chưa được tạo")
        return self.sessions[-1]


class FakeEmbeddingsByDict:
    """Trả vector tra theo text; TRẢ NGƯỢC thứ tự .data để chứng minh sort-by-index."""

    def __init__(self, mapping: dict[str, list[float]]):
        self.mapping = mapping
        self.calls: list[list[str]] = []

    def create(self, model: str, input: list[str]):  # noqa: A002 - khớp SDK
        self.calls.append(list(input))
        data = [
            FakeData(index=i, embedding=self.mapping[text])
            for i, text in enumerate(input)
        ]
        return SimpleNamespace(
            data=list(reversed(data)),  # cố tình xáo trộn — embedder phải sort lại
            usage=FakeUsage(prompt_tokens=len(input) * 7, completion_tokens=0),
        )


class FakeOpenAIClient:
    def __init__(self, embeddings):
        self.embeddings = embeddings


@pytest.fixture()
def dim3(monkeypatch):
    settings = embedder.get_settings()
    monkeypatch.setattr(settings, "EMBEDDING_DIM", DIM)
    return settings


@pytest.fixture()
def log_bucket(monkeypatch):
    """Thay _session_factory bằng recorder; trả bucket chứa các row đã add."""
    bucket: list = []
    factory = _FakeSessionFactory(bucket)
    monkeypatch.setattr(embedder, "_session_factory", factory)
    return bucket


def test_empty_input_no_call(dim3, monkeypatch):
    calls = {"n": 0}

    class _Probe:
        embeddings = None

    def _no_client():
        calls["n"] += 1
        return _Probe()

    monkeypatch.setattr(embedder, "_client", _no_client)
    assert embed_texts([]) == []
    assert calls["n"] == 0  # rỗng → không chạm provider, không tốn tiền


def test_batch_split_and_order_preserved(dim3, log_bucket, monkeypatch):
    texts = [f"cau so {i} da sanitize" for i in range(5)]  # 5 text → batch 2+2+1
    mapping = {t: [float(i), float(i) + 0.5, float(i) + 1] for i, t in enumerate(texts)}
    fake = FakeEmbeddingsByDict(mapping)
    monkeypatch.setattr(embedder, "_client", lambda: FakeOpenAIClient(fake))
    monkeypatch.setattr(embedder, "EMBED_BATCH_MAX_INPUTS", 2)

    vectors = embed_texts(texts)

    assert len(fake.calls) == 3
    assert [len(c) for c in fake.calls] == [2, 2, 1]
    assert all(len(c) <= EMBED_BATCH_MAX_INPUTS for c in fake.calls)
    # Thứ tự ĐÚNG input dù .data bị trả ngược trong từng batch.
    assert vectors == [mapping[t] for t in texts]
    # Mỗi call API ghi 1 row llm_call_logs call_type=embed.
    assert len(log_bucket) == 3
    row = log_bucket[0]
    assert row.call_type.value == "embed"
    assert row.model == dim3.EMBEDDING_MODEL
    assert row.prompt_tokens == 14  # 2 input × 7
    assert row.latency_ms >= 0
    assert row.error is None


def test_dim_mismatch_raises(dim3, log_bucket, monkeypatch):
    wrong = [[0.0] * (DIM + 1)]

    class _WrongDim:
        def create(self, model, input):  # noqa: A002
            return SimpleNamespace(
                data=[FakeData(index=i, embedding=wrong[i]) for i in range(len(input))],
                usage=FakeUsage(prompt_tokens=1, completion_tokens=0),
            )

    monkeypatch.setattr(embedder, "_client", lambda: FakeOpenAIClient(_WrongDim()))
    with pytest.raises(EmbeddingDimError, match="chiều"):
        embed_texts(["mot cau bat ky"])


def test_embed_one_returns_single_vector(dim3, log_bucket, monkeypatch):
    vec = [1.0, 2.0, 3.0]
    monkeypatch.setattr(
        embedder, "_client", lambda: FakeOpenAIClient(FakeEmbeddingsByDict({"xin chao": vec}))
    )
    assert embed_one("xin chao") == vec


def test_store_embedding_sets_three_columns(dim3):
    feedback = SimpleNamespace()
    store_embedding(None, feedback, [0.1, 0.2, 0.3])
    assert feedback.embedding == [0.1, 0.2, 0.3]
    assert feedback.embedding_model == dim3.EMBEDDING_MODEL
    assert feedback.embedding_dim == DIM

    with pytest.raises(EmbeddingDimError):
        store_embedding(None, SimpleNamespace(), [0.0] * (DIM + 5))


def test_log_failure_does_not_kill_flow(dim3, monkeypatch):
    """llm_call_logs hỏng (DB down…) → embedding VẪN thành công."""
    def _broken_factory():
        raise RuntimeError("db down")

    monkeypatch.setattr(embedder, "_session_factory", _broken_factory)
    monkeypatch.setattr(
        embedder,
        "_client",
        lambda: FakeOpenAIClient(FakeEmbeddingsByDict({"ok": [1.0, 2.0, 3.0]})),
    )
    assert embed_one("ok") == [1.0, 2.0, 3.0]
