"""Provider connections survive successive requests; no live provider calls."""

import httpx

from app.services import embedder, jev_client


def test_jev_second_request_does_not_use_a_closed_client(monkeypatch):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"answers": {}})
    ))
    monkeypatch.setattr(jev_client.httpx, "Client", lambda **kwargs: client)
    try:
        for _ in range(2):
            assert jev_client._post_systemone(
                {}, endpoint="https://example.test/systemone", api_key="synthetic"
            ) == {"answers": {}}
        assert not client.is_closed
    finally:
        close = getattr(jev_client, "close_client", client.close)
        close()


def test_embedding_requests_share_one_transport(monkeypatch):
    from openai import OpenAI

    clients = []

    def build_client(**kwargs):
        client = OpenAI(
            api_key="synthetic", base_url="https://example.test/v1",
            http_client=httpx.Client(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={
                    "object": "list", "model": "test", "usage": {"prompt_tokens": 1, "total_tokens": 1},
                    "data": [{"object": "embedding", "index": 0, "embedding": [1., 2., 3.]}],
                })
            )),
        )
        clients.append(client)
        return client

    monkeypatch.setattr(embedder, "OpenAI", build_client)
    monkeypatch.setattr(embedder.get_settings(), "EMBEDDING_DIM", 3)
    monkeypatch.setattr(embedder, "_log_call", lambda **kwargs: None)
    try:
        assert embedder.embed_one("synthetic one") == [1., 2., 3.]
        assert embedder.embed_one("synthetic two") == [1., 2., 3.]
        assert len(clients) == 1, "each item must reuse the provider connection pool"
    finally:
        close = getattr(embedder, "close_client", lambda: None)
        close()
        for client in clients:
            client.close()
