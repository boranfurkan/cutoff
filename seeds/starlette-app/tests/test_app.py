from starlette.testclient import TestClient

from web.app import app


def test_health_after_startup():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.json() == {"ready": True}
        assert r.headers["x-service"] == "demo"


def test_item():
    with TestClient(app) as client:
        assert client.get("/items/7").json() == {"id": 7}


def test_not_found():
    with TestClient(app) as client:
        r = client.get("/missing")
        assert r.status_code == 404 and r.text == "nope"
