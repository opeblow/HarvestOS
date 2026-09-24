import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

CHANNEL_SMS = "sms"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_RCS = "rcs"
CHANNEL_EMAIL = "email"
CHANNEL_IN_APP = "in_app"
CHANNELS = (CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_RCS, CHANNEL_EMAIL)

# Core delivery is always the in-app notification inbox. External channels are
# optional adapters that stay disabled until their provider is explicitly enabled.
IN_APP_PROVIDER = "in_app"
DISABLED_PROVIDER = "disabled"
EMAIL_PROVIDERS = (DISABLED_PROVIDER, "ses")
SMS_PROVIDERS = (DISABLED_PROVIDER, "eum")
WHATSAPP_PROVIDERS = (DISABLED_PROVIDER, "eum")

# Asset storage is local by default; S3 is an optional production adapter.
ASSET_STORAGE_LOCAL = "local"
ASSET_STORAGE_S3 = "s3"
ASSET_STORAGES = (ASSET_STORAGE_LOCAL, ASSET_STORAGE_S3)

SESSION_STORAGES = ("memory", "aws")


class ConfigError(RuntimeError):
    """Raised when the configuration is internally inconsistent.

    Core configuration must always be valid. Optional providers only fail when
    they are explicitly enabled but missing the settings they need.
    """


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    storage: str = "memory"
    agent_backend: str = "rule"

    region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    table_name: str = "harvestos-sessions"

    # Core notification delivery (in-app inbox) — always available.
    notification_provider: str = IN_APP_PROVIDER

    # Optional external delivery adapters. Disabled unless explicitly enabled.
    email_provider: str = DISABLED_PROVIDER
    sms_provider: str = DISABLED_PROVIDER
    whatsapp_provider: str = DISABLED_PROVIDER

    # Optional provider configuration (only required when the provider is enabled).
    ses_from_address: str = ""
    sms_origination_identity: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_linked_account_id: str = ""

    # Asset storage: local by default, S3 optional.
    asset_storage: str = ASSET_STORAGE_LOCAL
    asset_bucket: str = ""
    asset_local_dir: str = ".harvestos-assets"

    whatsapp_verify_token: str = "change-me-random-string"
    sms_webhook_auth_token: str = "change-me-random-string"

    sentry_dsn: str = ""
    paystack_secret_key: str = ""
    paystack_public_key: str = ""

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
    def asset_storage_is_s3(self) -> bool:
        return self.asset_storage.lower() == ASSET_STORAGE_S3

    @property
    def agent_backend_is_bedrock(self) -> bool:
        return self.agent_backend.lower() == "bedrock"

    @property
    def paystack_enabled(self) -> bool:
        return bool(self.paystack_secret_key)

    @property
    def email_enabled(self) -> bool:
        return self.email_provider.lower() != DISABLED_PROVIDER

    @property
    def sms_enabled(self) -> bool:
        return self.sms_provider.lower() != DISABLED_PROVIDER

    @property
    def whatsapp_enabled(self) -> bool:
        return self.whatsapp_provider.lower() != DISABLED_PROVIDER

    @property
    def external_channels(self) -> dict[str, str]:
        return {
            CHANNEL_SMS: self.sms_provider,
            CHANNEL_RCS: self.sms_provider,
            CHANNEL_WHATSAPP: self.whatsapp_provider,
            CHANNEL_EMAIL: self.email_provider,
        }

    def provider_for(self, channel: str) -> str:
        return self.external_channels.get(channel, DISABLED_PROVIDER)


settings = Settings()


def validate_settings(config: Settings | None = None) -> None:
    """Validate configuration, raising a clear error only for real problems.

    Core settings must always be coherent. Optional providers are validated
    only when explicitly enabled, so an unavailable SES/SMS/WhatsApp/S3 setup
    never stops the application from starting.
    """
    config = config or settings
    errors: list[str] = []

    if config.notification_provider.lower() != IN_APP_PROVIDER:
        errors.append(
            f"NOTIFICATION_PROVIDER must be '{IN_APP_PROVIDER}' "
            f"(got '{config.notification_provider}')"
        )

    if config.storage.lower() not in SESSION_STORAGES:
        errors.append(f"STORAGE must be one of {SESSION_STORAGES} (got '{config.storage}')")

    if config.email_provider.lower() not in EMAIL_PROVIDERS:
        errors.append(f"EMAIL_PROVIDER must be one of {EMAIL_PROVIDERS}")
    elif config.email_enabled and not config.ses_from_address:
        errors.append("EMAIL_PROVIDER=ses requires SES_FROM_ADDRESS")

    if config.sms_provider.lower() not in SMS_PROVIDERS:
        errors.append(f"SMS_PROVIDER must be one of {SMS_PROVIDERS}")
    elif config.sms_enabled and not config.sms_origination_identity:
        errors.append("SMS_PROVIDER=eum requires SMS_ORIGINATION_IDENTITY")

    if config.whatsapp_provider.lower() not in WHATSAPP_PROVIDERS:
        errors.append(f"WHATSAPP_PROVIDER must be one of {WHATSAPP_PROVIDERS}")
    elif config.whatsapp_enabled and not config.whatsapp_phone_number_id:
        errors.append("WHATSAPP_PROVIDER=eum requires WHATSAPP_PHONE_NUMBER_ID")

    if config.asset_storage.lower() not in ASSET_STORAGES:
        errors.append(f"ASSET_STORAGE must be one of {ASSET_STORAGES}")
    elif config.asset_storage_is_s3 and not config.asset_bucket:
        errors.append("ASSET_STORAGE=s3 requires ASSET_BUCKET")

    if (
        config.app_env.lower() in {"prod", "production"}
        and len(config.dashboard_session_secret) < 32
    ):
        errors.append("APP_ENV=prod requires HARVESTOS_SESSION_SECRET of at least 32 characters")

    if errors:
        raise ConfigError("Invalid HarvestOS configuration: " + "; ".join(errors))
