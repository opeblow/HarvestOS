from app.services.journey import JourneyService
from app.shared import Message


def test_journey_a_sms_escalates_to_whatsapp(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    service = JourneyService()

    receipts = service.handle_inbound(
        Message(
            channel="sms",
            from_number="+2347000000001",
            body="my maize leaves are turning yellow",
        )
    )

    session = service.store.get("+2347000000001")
    assert session.conversation[-1].body == "my maize leaves are turning yellow"
    assert any(r.channel == "sms" for r in receipts)
    # escalation to whatsapp requested should appear on the SMS side as instructions
    assert any("WhatsApp" in r.text or "wa.me" in r.text for r in receipts)


def test_journey_a_photo_triggers_quote_and_rcs_card(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    service = JourneyService()
    service.handle_inbound(
        Message(
            channel="sms",
            from_number="+2347000000002",
            body="my maize leaves are turning yellow",
        )
    )

    receipts = service.handle_inbound(
        Message(
            channel="whatsapp",
            from_number="+2347000000002",
            body="[photo uploaded]",
            media_url="media://leaf.jpg",
        )
    )

    session = service.store.get("+2347000000002")
    assert "diagnosis" in session.state
    assert "NPK151515" in str(session.state.get("product_sku"))
    rcs = [r for r in receipts if r.channel == "rcs"]
    assert len(rcs) >= 1
    assert session.visited_channels == ["sms", "whatsapp"] or len(session.visited_channels) >= 2


def test_journey_b_finance_requests_plan(monkeypatch):
    monkeypatch.setattr("app.config.settings.storage", "memory")
    monkeypatch.setattr("app.config.settings.paystack_secret_key", "")
    service = JourneyService()
    service.handle_inbound(
        Message(
            channel="sms",
            from_number="+2347000000003",
            body="my maize leaves are turning yellow",
        )
    )
    service.handle_inbound(
        Message(
            channel="whatsapp",
            from_number="+2347000000003",
            body="[photo uploaded]",
            media_url="media://leaf.jpg",
        )
    )
    service.handle_inbound(
        Message(channel="sms", from_number="+2347000000003", body="I can't afford it right now")
    )

    session = service.store.get("+2347000000003")
    assert session.state.get("finance_pending") is True

    service.handle_inbound(
        Message(channel="sms", from_number="+2347000000003", body="NAME Ade Oyo STATE Oyo")
    )

    session = service.store.get("+2347000000003")
    assert "loan_plan" in session.state
    plan = session.state["loan_plan"]
    assert plan["installments"] == 3
    assert plan["per_payment_ngn"] > 0
