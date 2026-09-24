import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

CHANNEL_SMS = "sms"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_RCS = "rcs"
CHANNEL_EMAIL = "email"
CHANNELS = (CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_RCS, CHANNEL_EMAIL)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    storage: str = "memory"
    agent_backend: str = "rule"

    region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    table_name: str = "harvestos-sessions"
    asset_bucket: str = ""
    ses_from_address: str = "harvestos@example.com"

    whatsapp_verify_token: str = "change-me-random-string"
    sms_webhook_auth_token: str = "change-me-random-string"

    sentry_dsn: str = ""
    paystack_secret_key: str = ""
    paystack_public_key: str = ""

    sms_origination_identity: str = ""
    whatsapp_linked_account_id: str = ""
    whatsapp_phone_number_id: str = ""

    ngrok_url: str = ""
    dashboard_origins: str = "http://localhost:3000,http://localhost:3001"
    dashboard_session_secret: str = Field(
        default="",
        validation_alias="HARVESTOS_SESSION_SECRET",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.dashboard_origins.split(",") if origin.strip()]

    @property
    def storage_is_aws(self) -> bool:
        return self.storage.lower() == "aws"

    @property
    def agent_backend_is_bedrock(self) -> bool:
        return self.agent_backend.lower() == "bedrock"

    @property
    def paystack_enabled(self) -> bool:
        return bool(self.paystack_secret_key)


settings = Settings()
