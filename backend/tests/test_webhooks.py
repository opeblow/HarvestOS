from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sms_webhook_rejects_bad_token():
    resp = client.post("/webhooks/sms?auth=wrong", json={"from": "+2348000000100", "body": "hi"})
    assert resp.status_code == 401


def test_sms_webhook_processes_message():
    resp = client.post(
        "/webhooks/sms",
        params={"auth": "change-me-random-string"},
        json={"from": "+2348000000101", "body": "hello"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert len(body["delivered"]) >= 1


def test_whatsapp_verify_handshake_ok():
    resp = client.get(
        "/webhooks/whatsapp",
        params={"hub.verify_token": "change-me-random-string", "hub.challenge": "987654321"},
    )
    assert resp.status_code == 200
    assert int(resp.text) == 987654321


def test_whatsapp_verify_handshake_rejected():
    resp = client.get(
        "/webhooks/whatsapp",
        params={"hub.verify_token": "nope", "hub.challenge": "987654321"},
    )
    assert resp.status_code == 403


def test_whatsapp_inbound_photo_roundtrip(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "+2348000000102",
                                    "id": "wamid.1",
                                    "type": "image",
                                    "image": {"id": "mid-photo-1"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    resp = client.post("/webhooks/whatsapp", json=payload)
    assert resp.status_code == 200


def test_healthz():
    resp = client.get("/healthz")
    assert resp.json()["ok"] is True
