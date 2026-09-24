from app.shared import Session
from app.shared.channel_policy import (
    TASK_DECISION_CARD,
    TASK_DOCUMENT,
    TASK_MEDIA_CAPTURE,
    pick_channel,
)


def test_media_capture_prefers_whatsapp():
    assert pick_channel(Session(phone_number="+2341"), TASK_MEDIA_CAPTURE) == "whatsapp"


def test_decision_card_prefers_rcs():
    assert pick_channel(Session(phone_number="+2341"), TASK_DECISION_CARD) == "rcs"


def test_document_prefers_email():
    assert pick_channel(Session(phone_number="+2341"), TASK_DOCUMENT) == "email"
