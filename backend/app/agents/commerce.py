from __future__ import annotations

import json
import math
import os
from functools import lru_cache

from app.agents.base import Agent
from app.shared import (
    ConversationTurn,
    Escalation,
    ProductQuote,
    RcsButton,
    RcsCard,
    Session,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dealers.json")

NITROGEN_SKU = "NPK151515"
DEFAULT_FARM_LAT = 7.3775
DEFAULT_FARM_LNG = 3.9470


@lru_cache(maxsize=1)
def _load_dealers() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as fh:
        return json.load(fh)["dealers"]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = map(math.radians, (lat1, lat2))
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return round(r * 2 * math.asin(math.sqrt(a)), 1)


class CommerceAgent(Agent):
    name = "commerce"

    def run(self, session: Session) -> ConversationTurn:
        product_match = session.state.get("product_sku", NITROGEN_SKU)
        quotes = self._quote(product_match)

        if not quotes:
            return ConversationTurn(
                intent="commerce",
                agent=self.name,
                reply_text=(
                    "Sorry, none of our verified dealers currently have that input in stock. "
                    "We will notify you the moment it arrives. Our support line can also help."
                ),
                data={"empty_stock": True},
            )

        best = quotes[0]
        session.state["quote"] = best.model_dump()

        card = RcsCard(
            title=best.product,
            description=(
                f"\u20a6{best.price_ngn:,.0f} \u00b7 {best.dealer} ({best.dealer_distance_km} km) "
                f"\u00b7 stock: {best.stock} bags\nTap RESERVE and pick it up at the dealer store."
            ),
            buttons=[
                RcsButton(title="Reserve for pickup", postback_data=f"RESERVE {best.sku}"),
                RcsButton(title="Need financing", postback_data="FINANCE HELP"),
            ],
        )

        reply = (
            f"Good news! {best.dealer} has {best.product} at \u20a6{best.price_ngn:,.0f} "
            f"({best.dealer_distance_km} km from your farm). I just sent you a card with a "
            "Reserve button — tap it to lock your pickup slot."
        )
        return ConversationTurn(
            intent="commerce",
            agent=self.name,
            reply_text=reply,
            card=card,
            escalation=Escalation(
                channel="rcs",
                reason="purchase decision needs a tap-through card",
                payload={"card": card.model_dump()},
            ),
            data={"quotes": [q.model_dump() for q in quotes], "next_intent": "finance"},
        )

    def _quote(self, sku: str) -> list[ProductQuote]:
        farm_lat = DEFAULT_FARM_LAT
        farm_lng = DEFAULT_FARM_LNG
        results: list[ProductQuote] = []
        for dealer in _load_dealers():
            for item in dealer["stock"]:
                if item["sku"] != sku:
                    continue
                distance = _haversine_km(farm_lat, farm_lng, dealer["lat"], dealer["lng"])
                results.append(
                    ProductQuote(
                        sku=item["sku"],
                        product=item["product"],
                        price_ngn=item["price_ngn"],
                        dealer=dealer["name"],
                        dealer_distance_km=distance,
                        stock=item["qty"],
                    )
                )
        return sorted(results, key=lambda q: (q.price_ngn, q.dealer_distance_km))
