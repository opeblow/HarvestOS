from __future__ import annotations

import requests

from app.agents.base import Agent
from app.config import settings
from app.shared import ConversationTurn, Escalation, LoanPlan, Session

FINANCE_INTENTS = (
    "finance",
    "loan",
    "pay later",
    "installment",
    "bnpl",
    "credit",
    "can't afford",
    "cant afford",
)


class FinanceAgent(Agent):
    name = "finance"

    def run(self, session: Session) -> ConversationTurn:
        text = (session.conversation[-1].body or "").lower()
        wants_finance = any(k in text for k in FINANCE_INTENTS)
        completing_kyc = bool(session.state.get("finance_pending")) and self._eligible(session)

        if not wants_finance and not completing_kyc:
            return ConversationTurn(
                intent="finance",
                agent=self.name,
                reply_text="",
                data={"eligible": False, "stage": "skip"},
            )

        quote = session.state.get("quote") or session.state.get("diagnosis", {})
        amount = float(quote.get("price_ngn", 0) if isinstance(quote, dict) else 0)
        if amount <= 0:
            amount = 18_500.0

        if not self._eligible(session):
            session.state["finance_pending"] = True
            return ConversationTurn(
                intent="finance",
                agent=self.name,
                reply_text=(
                    "I understand. To offer you a split-payment plan I need your full name and the "
                    "state where your farm is. Reply with: NAME <your name> and I'll set you up."
                ),
                escalation=Escalation(
                    channel="sms",
                    reason="basic KYC required",
                    payload={"kyc": ["name", "state"]},
                ),
                data={"eligible": False, "stage": "kyc_pending"},
            )

        session.state.pop("finance_pending", None)

        plan = LoanPlan(amount_ngn=amount, installments=3, per_payment_ngn=round(amount / 3, 2))
        plan.terms = (
            "3 equal weekly payments. No interest for the first 3 weeks at approved "
            "partner dealers."
        )
        pay_link = self._pay_installment_link(plan.per_payment_ngn)
        session.state["loan_plan"] = plan.model_dump()
        if pay_link:
            session.state["first_payment_url"] = pay_link

        reply = (
            f"You qualify for a HarvestOS split-payment: \u20a6{amount:,.0f} in "
            f"{plan.installments} payments of \u20a6{plan.per_payment_ngn:,.2f} "
            f"(ref {plan.agreement_id}). The formal agreement is on its way to your "
            "email — reply OK to accept."
        )
        return ConversationTurn(
            intent="finance",
            agent=self.name,
            reply_text=reply,
            escalation=Escalation(
                channel="email",
                reason="loan agreement must be retained",
                payload={"agreement_id": plan.agreement_id},
            ),
            data={"loan_plan": plan.model_dump(), "payment_url": pay_link or ""},
        )

    @staticmethod
    def _eligible(session: Session) -> bool:
        kyc = session.state.get("kyc", {})
        return bool(kyc.get("name")) and bool(kyc.get("state"))

    @staticmethod
    def _pay_installment_link(amount: float) -> str:
        if not settings.paystack_enabled:
            return ""
        try:
            resp = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
                json={
                    "email": "farmer@harvestos.ng",
                    "amount": int(amount * 100),
                    "currency": "NGN",
                },
                timeout=10,
            )
            data = resp.json()
        except requests.RequestException:
            return ""
        return data.get("data", {}).get("authorization_url", "") if data.get("status") else ""
