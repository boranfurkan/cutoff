from fastapi.testclient import TestClient

from api.main import app


def test_seeded():
    with TestClient(app) as c:
        assert c.get("/items").json() == [{"name": "widget", "qty": 3}]


def test_prefix_validation():
    with TestClient(app) as c:
        assert c.get("/items", params={"prefix": "W1"}).status_code == 422


def test_add():
    with TestClient(app) as c:
        assert c.post("/items", json={"name": "bolt", "qty": 9}).json() == {"name": "bolt", "qty": 9}


def test_docs_prefix():
    with TestClient(app) as c:
        assert c.get("/openapi.json").json()["servers"] == [{"url": "/api"}]
