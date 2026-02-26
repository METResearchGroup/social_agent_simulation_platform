import json

import httpx
from fastapi.testclient import TestClient

from gateway.api.main import create_app
from gateway.api.settings import GatewaySettings


def test_proxy_forwards_path_query_method_and_body_and_filters_hop_by_hop_headers():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/simulations/run"
        assert request.url.query == b"foo=bar"
        assert request.headers.get("host") is not None  # httpx sets host internally
        assert request.headers.get("content-length") is not None  # computed by httpx
        # Our proxy removes hop-by-hop headers from inbound request; ensure caller-provided ones are gone.
        assert request.headers.get("upgrade") is None
        assert request.headers.get("proxy-authorization") is None
        assert request.headers.get("accept-encoding") == "identity"
        assert json.loads(request.content.decode()) == {"x": 1}
        return httpx.Response(
            status_code=201,
            headers={
                "Content-Type": "application/json",
                "Connection": "close",
                "X-Upstream": "1",
            },
            json={"ok": True},
        )

    transport = httpx.MockTransport(handler)
    settings = GatewaySettings(
        upstream_base_url="http://upstream",
        timeout_seconds=1.0,
        allowed_origins_raw="http://localhost:3000",
    )
    app = create_app(settings=settings)
    app.state.http_transport = transport

    with TestClient(app) as client:
        resp = client.post(
            "/v1/simulations/run?foo=bar",
            headers={
                "Connection": "keep-alive",
                "Upgrade": "websocket",
                "Proxy-Authorization": "secret",
                "X-Request-ID": "abc123",
            },
            json={"x": 1},
        )

    assert resp.status_code == 201
    assert resp.json() == {"ok": True}
    assert resp.headers.get("x-upstream") == "1"
    assert resp.headers.get("connection") is None
    assert resp.headers.get("x-request-id") == "abc123"


def test_proxy_timeout_maps_to_504():
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        raise httpx.ReadTimeout("boom")

    transport = httpx.MockTransport(handler)
    settings = GatewaySettings(
        upstream_base_url="http://upstream",
        timeout_seconds=0.01,
        allowed_origins_raw="http://localhost:3000",
    )
    app = create_app(settings=settings)
    app.state.http_transport = transport

    with TestClient(app) as client:
        resp = client.get("/v1/simulations/metrics")

    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
