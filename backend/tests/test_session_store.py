from app.config import settings
from app.shared import Message
from app.shared.session_store import InMemorySessionStore, SessionStoreFactory


def test_append_creates_and_persists_session():
    store = InMemorySessionStore()
    msg = Message(channel="sms", from_number="+2348000000001", body="hello")
    session = store.append_message("+2348000000001", msg)

    assert session.phone_number == "+2348000000001"
    assert session.visited_channels == ["sms"]
    assert len(session.conversation) == 1
    assert store.get("+2348000000001") is session


def test_dedupes_replayed_message_id():
    store = InMemorySessionStore()
    msg = Message(channel="sms", from_number="+2348000000002", body="hi", message_id="same-id")
    store.append_message("+2348000000002", msg)
    store.append_message("+2348000000002", msg)

    session = store.get("+2348000000002")
    assert len(session.conversation) == 1


def test_channel_migration_tracks_visited_channels():
    store = InMemorySessionStore()
    store.append_message(
        "+2348000000003",
        Message(channel="sms", from_number="+2348000000003", body="a"),
    )
    store.append_message(
        "+2348000000003",
        Message(channel="whatsapp", from_number="+2348000000003", body="b"),
    )

    session = store.get("+2348000000003")
    assert session.visited_channels == ["sms", "whatsapp"]
    assert session.channel == "whatsapp"


def test_factory_respects_storage_setting(monkeypatch):
    monkeypatch.setattr(settings, "storage", "memory")
    store = SessionStoreFactory.create(settings)
    assert isinstance(store, InMemorySessionStore)


def test_session_roundtrips_via_factory(monkeypatch):
    monkeypatch.setattr(settings, "storage", "memory")
    store = SessionStoreFactory.create(settings)
    store.append_message(
        "+2348000000004",
        Message(channel="sms", from_number="+2348000000004", body="x"),
    )
    assert store.get("+2348000000004") is not None
