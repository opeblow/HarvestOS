from __future__ import annotations

from app.agents.base import Agent
from app.shared import ConversationTurn, Session


class LogisticsAgent(Agent):
    name = "logistics"

    def run(self, session: Session) -> ConversationTurn:
        quote = session.state.get("quote") or {}
        if not quote:
            return ConversationTurn(
                intent="logistics",
                agent=self.name,
                reply_text="",
                data={"stage": "idle"},
            )

        dealer = quote.get("dealer", "the partner dealer")
        text = (session.conversation[-1].body or "").upper()
        if text == "OK" or "CONFIRM" in text or "yes" in text.lower():
            session.state["order_status"] = "confirmed_pickup"
            return ConversationTurn(
                intent="logistics",
                agent=self.name,
                reply_text=(
                    f"Your reservation at {dealer} is confirmed. Pickup any day within your "
                    "window; show the reference on arrival. We'll also send a reminder in 14 days."
                ),
                data={"stage": "confirmed", "pickup": True},
            )

        return ConversationTurn(
            intent="logistics",
            agent=self.name,
            reply_text=(
                "Pickup is ready when you reserve. Reply OK to confirm your slot at the dealer "
                "store, or FINANCE to split the payment."
            ),
            data={"stage": "awaiting_confirm"},
        )
