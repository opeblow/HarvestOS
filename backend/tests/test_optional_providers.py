import pytest

from app.channels.factory import ChannelRegistry
from app.config import ConfigError, Settings, validate_settings
from app.notifications.service import NotificationService
from app.notifications.store import InMemoryNotificationStore
from app.shared import OutboundMessage, ProviderError
from app.storage.factory import AssetStorageFactory
from app.storage.local import LocalAssetStorage
from app.storage.s3 import S3AssetStorage


def _service() -> NotificationService:
    return NotificationService(InMemoryNotificationStore(), ChannelRegistry())


def test_core_config_is_valid_without_any_optional_provider():
    validate_settings(Settings())


def test_disabled_external_providers_do_not_block_delivery():
    service = _service()
    receipt = service.deliver(
        OutboundMessage(channel="sms", to="+2347000000001", text="hello", category="system")
    )

    assert receipt.provider == "in_app"
    assert receipt.delivered is True
    stored = service.list()
    assert len(stored) == 1
    assert stored[0].channel == "sms"
    assert stored[0].delivered_externally is False


def test_disabled_provider_raises_clear_error_when_used_directly():
    registry = ChannelRegistry()
    with pytest.raises(ProviderError):
        registry.dispatch("email").send(
            OutboundMessage(channel="email", to="farmer@example.com", text="hi")
        )


def test_notification_inbox_read_lifecycle():
    service = _service()
    service.deliver(
        OutboundMessage(channel="rcs", to="+2347000000002", text="card", category="commerce")
    )

    assert service.unread_count() == 1
    notification = service.list()[0]
    service.mark_read(notification.id)
    assert service.unread_count() == 0


def test_enabling_provider_without_config_is_a_config_error():
    config = Settings(email_provider="ses", ses_from_address="")
    with pytest.raises(ConfigError):
        validate_settings(config)


def test_enabling_sms_without_origination_identity_is_a_config_error():
    config = Settings(sms_provider="eum", sms_origination_identity="")
    with pytest.raises(ConfigError):
        validate_settings(config)


def test_s3_asset_storage_requires_bucket():
    config = Settings(asset_storage="s3", asset_bucket="")
    with pytest.raises(ConfigError):
        validate_settings(config)


def test_asset_storage_defaults_to_local():
    assert isinstance(AssetStorageFactory.create(Settings()), LocalAssetStorage)


def test_asset_storage_uses_s3_when_configured():
    storage = AssetStorageFactory.create(
        Settings(asset_storage="s3", asset_bucket="harvestos-assets")
    )
    assert isinstance(storage, S3AssetStorage)


def test_local_asset_storage_roundtrip(tmp_path):
    storage = LocalAssetStorage(str(tmp_path))
    ref = storage.save("photos/leaf.jpg", b"image-bytes", "image/jpeg")

    assert ref == "local://photos/leaf.jpg"
    assert storage.load(ref) == b"image-bytes"
