from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

TEXT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2"
VISION_MODEL = TEXT_MODEL


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str, image: bytes | None = None) -> str: ...


class RuleBackend(LLMClient):
    def complete(self, system: str, prompt: str, image: bytes | None = None) -> str:
        lower = prompt.lower()
        if image:
            if "yellow" in lower or "nitrogen" in lower or "maize" in lower:
                return (
                    "Likely nitrogen deficiency. Lower leaves yellow first, starting at the tip "
                    "and moving along the midrib toward the stem."
                )
            if "burn" in lower or "brown" in lower:
                return "Possible scorch from over-fertilisation or heat stress."
            return "Symptoms match a mild nutrient stress pattern; recommend nitrogen top-dressing."
        if "price" in lower or "buy" in lower:
            return ""
        return "I have no additional signal from a text-only prompt."


class BedrockBackend(LLMClient):
    def __init__(self) -> None:
        self._runtime = boto3.client("bedrock-runtime", region_name=settings.region)

    def complete(self, system: str, prompt: str, image: bytes | None = None) -> str:
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    [
                        {"image": {"source": {"bytes": base64.b64encode(image).decode()}}},
                        {"text": prompt},
                    ]
                    if image
                    else [{"text": prompt}]
                ),
            }
        ]
        try:
            resp = self._runtime.converse(
                modelId=VISION_MODEL if image else TEXT_MODEL,
                system=[{"text": system}],
                messages=messages,
                inferenceConfig={"maxTokens": 1024, "temperature": 0},
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Bedrock Converse failed: {exc}") from exc
        return resp["output"]["message"]["content"][0]["text"]


class LLMFactory:
    @staticmethod
    def create() -> LLMClient:
        return BedrockBackend() if settings.agent_backend_is_bedrock else RuleBackend()
