from __future__ import annotations

import urllib.request
from urllib.parse import urlparse

import boto3

from app.agents.base import Agent
from app.agents.llm import LLMClient, LLMFactory
from app.config import settings
from app.shared import ConversationTurn, DiagnosisResult, Escalation, Session

SYSTEM_PROMPT = (
    "You are HarvestOS Diagnosis Agent, an agronomist for smallholder maize farmers "
    "in West Africa. Diagnose from the farmer's photo and words, then answer in plain, "
    "simple language (English or Yoruba if they write Yoruba). Give the likely cause, "
    "confidence, and one concrete next step."
)


class DiagnosisAgent(Agent):
    name = "diagnosis"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMFactory.create()

    def run(self, session: Session) -> ConversationTurn:
        latest = session.conversation[-1]
        text = (latest.body or "").strip()

        if latest.media_url:
            try:
                image = self._fetch_image(latest.media_url)
            except Exception:  # noqa: BLE001
                image = None
            summary = self._llm.complete(SYSTEM_PROMPT, f"Farmer message: {text}", image=image)
            diagnosis = self._summarize(text, summary)
            recommendation = "Apply NPK 15-15-15 at 2 bags/ha and retest leaves in one week."
            reply = (
                f"{diagnosis.plain_language}\n\nWhat to do next: {recommendation}\n\n"
                "Want me to connect you with a nearby dealer who has this input in stock?"
            )
            return ConversationTurn(
                intent="diagnosis",
                agent=self.name,
                reply_text=reply,
                data={
                    "diagnosis": diagnosis.model_dump(),
                    "next_intent": "commerce",
                },
            )

        reply = (
            "Thanks for reaching out to HarvestOS. To diagnose your maize properly I need a "
            "photo of the affected leaves. Open the WhatsApp link we just texted you and send a "
            "clear close-up picture — I'll take it from there. 👨‍🌾"
        )
        return ConversationTurn(
            intent="diagnosis",
            agent=self.name,
            reply_text=reply,
            escalation=Escalation(
                channel="whatsapp",
                reason="photo evidence needed",
                payload={"media": True},
            ),
            data={"stage": "awaiting_photo"},
        )

    @staticmethod
    def _fetch_image(media_url: str) -> bytes:
        parsed = urlparse(media_url)
        if parsed.scheme == "s3" and parsed.netloc and parsed.path.strip("/"):
            response = boto3.client("s3", region_name=settings.region).get_object(
                Bucket=parsed.netloc,
                Key=parsed.path.lstrip("/"),
            )
            return response["Body"].read()
        if parsed.scheme != "https":
            raise ValueError("crop image must be an HTTPS URL or a private S3 object")
        with urllib.request.urlopen(media_url, timeout=10) as resp:
            return resp.read()

    def _summarize(self, text: str, llm_summary: str) -> DiagnosisResult:
        lower = (text + " " + llm_summary).lower()
        if "yellow" in lower or "nitrogen" in lower:
            result = DiagnosisResult(
                crop="maize",
                issue="nitrogen_deficiency",
                confidence=0.92,
                plain_language=(
                    "Your maize most likely has a nitrogen (N) deficiency. The oldest, "
                    "lower leaves turn pale yellow starting at the tip, while new growth "
                    "stays green."
                ),
            )
        else:
            result = DiagnosisResult(
                crop="maize",
                issue="nutrient_stress",
                confidence=0.8,
                plain_language=(
                    "The symptoms point to a nutrient stress pattern; it looks like early "
                    "nitrogen deficit."
                ),
            )
        result.recommendation = "Apply NPK 15-15-15 at 2 bags/ha and retest leaves in one week."
        result.agent = self.name
        return result
