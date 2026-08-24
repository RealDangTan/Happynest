"""Integration roundtrip /similar trên PostgreSQL thật (Supabase).

⚠️ Marker `integration` — chạy riêng: `uv run pytest -m integration`
(cần backend/.env có DATABASE_URL hợp lệ + internet; DB dev chỉ nhận data FAKE).

Không gọi API embeddings — insert embedding TAY bằng vector đơn vị dễ đoán
cosine, kiểm chứng đúng checklist plan 08 §3.4:
- store_embedding lưu đủ 3 cột (embedding + embedding_model + embedding_dim);
- exact scan rank ĐÚNG thứ tự kỳ vọng theo cosine giảm dần;
- loại chính row truy vấn (self excluded);
- thiếu embedding → 409; k ngoài [1..50] → 422.
"""

import math
import uuid
from datetime import datetime, timezone

import pytest

from app.db.session import SessionLocal
from app.models.feedback import Feedback
from app.services.embedder import store_embedding

pytestmark = pytest.mark.integration

DIM = 1536  # khớp VECTOR(1536) cứng trong model Feedback

SOURCE = "test-similarity"  # marker để nhận diện + dọn sạch


def _vec(coords: dict[int, float]) -> list[float]:
    """Vector đơn vị 1536-d với giá trị khác 0 ở các index cho trước."""
    raw = [0.0] * DIM
    for idx, val in coords.items():
        raw[idx] = float(val)
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


# Cosine so với A = e_0, tất cả KHÁC NHAU → thứ tự exact scan all-deterministic.
VECS = {
    "A": _vec({0: 1}),                                   # truy vấn chính (cos = 1)
    "B": _vec({0: 0.99, 1: math.sqrt(1 - 0.99**2)}),      # cos(A,B) = 0.99
    "C": _vec({1: 1}),                                    # cos(A,C) = 0
    "E": _vec({0: -math.sqrt(0.5), 2: math.sqrt(0.5)}),   # cos(A,E) ≈ -0.707
    "D": _vec({0: -1}),                                   # cos(A,D) = -1
}
EXPECTED_ORDER = ["B", "C", "E", "D"]  # similarity giảm dần quanh A


@pytest.fixture()
def sim_ids():
    """Insert 5 feedback fake kèm embedding tay qua store_embedding; dọn sạch sau."""
    ids: dict[str, uuid.UUID] = {}
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for name, vec in VECS.items():
            fb = Feedback(
                source=SOURCE,
                created_at=now,
                raw_content=f"fake noi dung {name} cho test similarity (khong PII)",
                sanitized_content=f"sanitized {name}",
            )
            db.add(fb)
            db.flush()  # lấy id trước khi gắn vector
            store_embedding(db, fb, vec)
            ids[name] = fb.id
        db.commit()

        # DoD mục 6: vector lưu KÈM model+dim — đối chiếu ngay trên DB thật.
        row = db.get(Feedback, ids["A"])
        assert row.embedding_model, "embedding_model phải được set cùng lúc"
        assert row.embedding_dim == DIM
        assert len(row.embedding) == DIM

    try:
        yield ids
    finally:
        with SessionLocal() as db:
            for fid in ids.values():
                obj = db.get(Feedback, fid)
                if obj is not None:
                    db.delete(obj)
            db.commit()


def test_similarity_rank_order(client, sim_ids):
    resp = client.get(f"/api/feedbacks/{sim_ids['A']}/similar?k=10")
    assert resp.status_code == 200, resp.text
    items = resp.json()

    returned_names = {
        next(n for n, fid in sim_ids.items() if str(fid) == item["id"]): item
        for item in items
    }

    # Self excluded + đủ 4 hàng xóm còn lại.
    assert "A" not in returned_names
    assert set(returned_names) == set(EXPECTED_ORDER)

    got_order = [item["id"] for item in items]
    expected = [str(sim_ids[n]) for n in EXPECTED_ORDER]
    assert got_order == expected, f"rank sai: {got_order} != {expected}"

    # Score giảm dần; giá trị cosine khớp lý thuyết (tolerance số thực).
    scores = [item["score"] for item in items]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(0.99, abs=1e-3)   # B
    assert scores[1] == pytest.approx(0.0, abs=1e-6)    # C
    assert scores[2] == pytest.approx(-math.sqrt(0.5), abs=1e-3)  # E
    assert scores[3] == pytest.approx(-1.0, abs=1e-6)   # D

    item_b = returned_names["B"]
    assert item_b["source"] == SOURCE
    assert item_b["snippet"] == "sanitized B"[:200]


def test_similar_missing_embedding_409(client):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        fb = Feedback(
            source=SOURCE,
            created_at=now,
            raw_content="fake chua co embedding",
            sanitized_content="sanitized",
        )
        db.add(fb)
        db.commit()
        fid = fb.id
    try:
        resp = client.get(f"/api/feedbacks/{fid}/similar")
        assert resp.status_code == 409
        assert "embedding" in resp.json()["detail"].lower()
    finally:
        with SessionLocal() as db:
            obj = db.get(Feedback, fid)
            if obj is not None:
                db.delete(obj)
            db.commit()


def test_similar_unknown_id_404(client):
    resp = client.get(f"/api/feedbacks/{uuid.uuid4()}/similar")
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_k", ["0", "51"])
def test_similar_k_out_of_range_422(client, sim_ids, bad_k):
    resp = client.get(f"/api/feedbacks/{sim_ids['A']}/similar?k={bad_k}")
    assert resp.status_code == 422
