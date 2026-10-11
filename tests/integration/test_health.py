def test_liveness(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_readiness_reports_every_dependency(client):
    body = client.get("/health/ready").json()
    assert body == {"status": "ok", "checks": {"database": "ok", "valkey": "ok", "storage": "ok"}}


def test_readiness_fails_when_the_storage_is_down(client, storage, monkeypatch):
    monkeypatch.setattr(storage, "is_reachable", lambda: False)
    response = client.get("/health/ready")
    assert response.status_code == 503 and response.json()["checks"]["storage"] == "error"


def test_every_response_carries_a_request_id(client):
    assert client.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    assert client.get("/health").headers["X-Request-ID"]
    assert client.get("/health", headers={"X-Request-ID": "bad id\r\n"}).headers["X-Request-ID"] != "bad id"


def test_cors_allows_the_frontend_and_nobody_else(client):
    asked = {"Access-Control-Request-Method": "GET"}
    allowed = client.options("/api/v1/courses", headers={"Origin": "http://localhost:5173", **asked})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    foreign = client.options("/api/v1/courses", headers={"Origin": "http://evil.example", **asked})
    assert "access-control-allow-origin" not in foreign.headers
