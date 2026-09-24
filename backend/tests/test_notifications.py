from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_notifications_are_recorded_and_readable(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    client.post(
        "/webhooks/sms",
        params={"auth": "change-me-random-string"},
        json={"from": "+2347000000123", "body": "my maize leaves are turning yellow"},
    )

    resp = client.get("/api/notifications")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["unread"] >= 1
    first = body["items"][0]
    assert {"id", "category", "title", "body", "read_ts"} <= set(first)

    read = client.post(f"/api/notifications/{first['id']}/read")
    assert read.status_code == 200
    assert read.json()["ok"] is True


def test_marking_unknown_notification_returns_404():
    resp = client.post("/api/notifications/does-not-exist/read")
    assert resp.status_code == 404


def test_read_all_clears_unread():
    client.post(
        "/webhooks/sms",
        params={"auth": "change-me-random-string"},
        json={"from": "+2347000000456", "body": "my maize leaves are turning yellow"},
    )

    resp = client.post("/api/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json()["unread"] == 0
