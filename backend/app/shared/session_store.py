from __future__ import annotations

import json
from abc import ABC, abstractmethod

import boto3
from botocore.exceptions import ClientError

from app.config import Settings
from app.shared import Message, Session


class SessionStore(ABC):
    @abstractmethod
    def get(self, phone_number: str) -> Session | None: ...

    @abstractmethod
    def put(self, session: Session) -> Session: ...

    @abstractmethod
    def append_message(self, phone_number: str, message: Message) -> Session: ...

    @abstractmethod
    def list_sessions(self, limit: int = 200) -> list[Session]: ...


def _append(session: Session, message: Message) -> Session:
    if any(m.message_id == message.message_id for m in session.conversation):
        return session
    if message.channel not in session.visited_channels:
        session.visited_channels.append(message.channel)
    session.channel = message.channel
    session.conversation.append(message)
    session.touch()
    return session


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    def get(self, phone_number: str) -> Session | None:
        return self._store.get(phone_number)

    def put(self, session: Session) -> Session:
        self._store[session.phone_number] = session
        return session

    def append_message(self, phone_number: str, message: Message) -> Session:
        session = self.get(phone_number) or Session(phone_number=phone_number)
        return self.put(_append(session, message))

    def list_sessions(self, limit: int = 200) -> list[Session]:
        sessions = list(self._store.values())
        sessions.sort(key=lambda s: s.updated_ts, reverse=True)
        return sessions[:limit]


class DynamoDBSessionStore(SessionStore):
    PK = "pk"
    SK = "sk"
    META_SK = "meta"

    def __init__(self, settings: Settings) -> None:
        region = settings.region
        self._table = boto3.resource("dynamodb", region_name=region).Table(settings.table_name)

    def get(self, phone_number: str) -> Session | None:
        resp = self._table.get_item(Key={self.PK: phone_number, self.SK: self.META_SK})
        raw = resp.get("Item")
        if raw is None:
            return None
        return Session.model_validate(json.loads(raw["document"]))

    def put(self, session: Session) -> Session:
        try:
            self._table.put_item(
                Item={
                    self.PK: session.phone_number,
                    self.SK: self.META_SK,
                    "document": session.model_dump_json(),
                }
            )
        except ClientError as exc:
            raise RuntimeError(f"failed to persist session for {session.phone_number}") from exc
        return session

    def append_message(self, phone_number: str, message: Message) -> Session:
        session = self.get(phone_number) or Session(phone_number=phone_number)
        return self.put(_append(session, message))

    def list_sessions(self, limit: int = 200) -> list[Session]:
        resp = self._table.scan(Limit=limit)
        sessions = [
            Session.model_validate(json.loads(item["document"])) for item in resp.get("Items", [])
        ]
        sessions.sort(key=lambda s: s.updated_ts, reverse=True)
        return sessions


class SessionStoreFactory:
    @staticmethod
    def create(settings: Settings) -> SessionStore:
        if settings.storage_is_aws:
            return DynamoDBSessionStore(settings)
        return InMemorySessionStore()
