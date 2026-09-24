from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared import ConversationTurn, Session


class Agent(ABC):
    name: str

    @abstractmethod
    def run(self, session: Session) -> ConversationTurn: ...
