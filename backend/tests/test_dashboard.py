from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_stats_empty_store():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions"] >= 0
    assert set(body["channel_messages"]) == {"sms", "whatsapp", "rcs", "email"}


def test_conversations_lists_driven_session(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    client.post(
        "/webhooks/sms",
        params={"auth": "change-me-random-string"},
        json={"from": "+2347000000099", "body": "my maize leaves are turning yellow"},
    )

    resp = client.get("/api/conversations")
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    mine = [r for r in rows if r["phone"].endswith("0099")]
    assert mine
    assert "yellow" in mine[0]["last_message"]
    assert "****" in mine[0]["phone"]


def test_loan_health_shape():
    resp = client.get("/api/loan-health")
    assert resp.status_code == 200
    body = resp.json()
    assert "active_loans" in body
    assert "portfolio_ngn" in body


def test_dealers_listing():
    resp = client.get("/api/dealers")
    assert resp.status_code == 200
    dealers = resp.json()
    assert len(dealers) >= 1
    assert any("stock" in d for d in dealers)
