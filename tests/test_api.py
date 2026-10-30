"""Unit tests. Run with:  pytest -v

Each test gets a fresh in-memory SQLite database, so tests never touch real data.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keep one in-memory DB shared across connections
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No "with" block on purpose: the startup hook (real DB) must not run in tests.
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def register(client, username="alice", password="supersecret1"):
    return client.post("/auth/register", json={"username": username, "password": password})


def login_headers(client, username="alice", password="supersecret1"):
    register(client, username, password)
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------- basic ----------
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------- auth ----------
def test_register_success(client):
    resp = register(client)
    assert resp.status_code == 201
    assert resp.json()["username"] == "alice"
    assert "password" not in resp.json()


def test_register_duplicate_username(client):
    register(client)
    assert register(client).status_code == 409


def test_register_rejects_short_password(client):
    assert register(client, password="short").status_code == 422


def test_login_wrong_password(client):
    register(client)
    resp = client.post("/auth/login", data={"username": "alice", "password": "wrongpass1"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", data={"username": "nobody", "password": "whatever123"})
    assert resp.status_code == 401


def test_urls_require_authentication(client):
    resp = client.post("/urls", json={"target_url": "https://example.com"})
    assert resp.status_code == 401


def test_invalid_token_rejected(client):
    resp = client.get("/urls", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


# ---------- shortening and redirect ----------
def test_create_and_redirect_counts_clicks(client):
    headers = login_headers(client)
    created = client.post("/urls", json={"target_url": "https://example.com/page"}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert len(body["code"]) == 6
    assert body["short_url"].endswith("/" + body["code"])
    assert body["clicks"] == 0

    for _ in range(2):
        redirect = client.get(f"/{body['code']}", follow_redirects=False)
        assert redirect.status_code == 307
        assert redirect.headers["location"] == "https://example.com/page"

    stats = client.get(f"/urls/{body['code']}", headers=headers)
    assert stats.json()["clicks"] == 2


def test_custom_code_and_conflict(client):
    headers = login_headers(client)
    first = client.post(
        "/urls", json={"target_url": "https://example.com", "custom_code": "my-link"}, headers=headers
    )
    assert first.status_code == 201
    assert first.json()["code"] == "my-link"

    second = client.post(
        "/urls", json={"target_url": "https://other.com", "custom_code": "my-link"}, headers=headers
    )
    assert second.status_code == 409


def test_reserved_code_rejected(client):
    headers = login_headers(client)
    resp = client.post(
        "/urls", json={"target_url": "https://example.com", "custom_code": "docs"}, headers=headers
    )
    assert resp.status_code == 409


def test_invalid_target_url_rejected(client):
    headers = login_headers(client)
    resp = client.post("/urls", json={"target_url": "not-a-url"}, headers=headers)
    assert resp.status_code == 422


def test_unknown_code_returns_404(client):
    assert client.get("/doesnotexist", follow_redirects=False).status_code == 404


# ---------- ownership ----------
def test_list_returns_only_own_urls(client):
    alice = login_headers(client, "alice")
    bob = login_headers(client, "bob")
    client.post("/urls", json={"target_url": "https://a.example.com"}, headers=alice)
    client.post("/urls", json={"target_url": "https://b.example.com"}, headers=bob)

    alice_urls = client.get("/urls", headers=alice).json()
    assert len(alice_urls) == 1
    assert alice_urls[0]["target_url"].startswith("https://a.example.com")


def test_delete_own_url(client):
    headers = login_headers(client)
    code = client.post("/urls", json={"target_url": "https://example.com"}, headers=headers).json()["code"]

    assert client.delete(f"/urls/{code}", headers=headers).status_code == 204
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404


def test_cannot_delete_someone_elses_url(client):
    alice = login_headers(client, "alice")
    bob = login_headers(client, "bob")
    code = client.post("/urls", json={"target_url": "https://example.com"}, headers=alice).json()["code"]

    assert client.delete(f"/urls/{code}", headers=bob).status_code == 404
    # Still works for the public
    assert client.get(f"/{code}", follow_redirects=False).status_code == 307
