import os

import pytest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret"
from app import make_app, db

@pytest.fixture()
def client():
    app = make_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context(): db.drop_all(); db.create_all()
    with app.test_client() as c:
        c.get("/api/config")
        yield c
    with app.app_context(): db.drop_all()

def token(c): return c.get("/api/config").get_json()["csrf"]
def post(c, url, data): return c.post(url, json=data, headers={"X-CSRF-Token":token(c)})

def register(c, username="mira"):
    return post(c,"/api/register",{"name":"Mira","username":username,"email":username+"@example.com","password":"a-long-test-password"})

def test_register_login_logout_persistence(client):
    assert register(client).status_code == 200
    assert client.get("/api/session").get_json()["user"]["username"] == "mira"
    client.post("/api/logout",headers={"X-CSRF-Token":token(client)})
    assert client.get("/api/session").get_json()["user"] is None
    assert post(client,"/api/login",{"identifier":"mira","password":"a-long-test-password"}).status_code == 200

def test_profile_mood_diary_are_profile_scoped(client):
    assert register(client).status_code == 200
    first=client.get("/api/session").get_json()["active"]
    assert post(client,"/api/moods",{"mood":"Calm"}).status_code == 400
    assert post(client,"/api/moods",{"mood":"Happy"}).status_code == 200
    assert post(client,"/api/diary",{"title":"A note","body":"Private thought"}).status_code == 200
    p=post(client,"/api/profiles",{"name":"Family","kind":"Family"}).get_json()
    assert post(client,f"/api/profiles/{p['id']}/switch",{}).status_code == 200
    assert client.get("/api/moods").get_json() == []
    assert client.get("/api/diary").get_json() == []
    assert post(client,f"/api/profiles/{first}/switch",{}).status_code == 200
    assert len(client.get("/api/moods").get_json()) == 1
    assert len(client.get("/api/diary").get_json()) == 1

def test_duplicate_registration_and_csrf(client):
    assert register(client).status_code == 200
    assert register(client).status_code == 409
    assert client.post("/api/logout").status_code == 403

def test_ai_fails_closed_without_secret(client,monkeypatch):
    assert register(client).status_code == 200
    monkeypatch.delenv("EMERGENT_API_KEY",raising=False)
    result=post(client,"/api/ai/text",{"text":"I had a difficult day"})
    assert result.status_code == 503
    assert "manually" in result.get_json()["error"]
