from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alert.notifications import send_email


@pytest.mark.asyncio
@patch("src.alert.notifications.get_settings")
@patch("src.alert.notifications.logger")
async def test_send_email_success(mock_logger, mock_get_settings):
    # Mock config
    mock_settings = AsyncMock()
    mock_settings.SMTP_FROM = "noreply@example.com"
    mock_get_settings.return_value = mock_settings

    to = "user@example.com"
    subject = "Test Subject"
    body = "Test Body"

    await send_email(to, subject, body)

    # Check that logging occurred
    mock_logger.info.assert_called_once_with(f"Email sent to {to}: {subject}")


@pytest.mark.asyncio
@patch("src.alert.notifications.get_settings")
@patch("src.alert.notifications.logger")
async def test_send_email_failure_logging(mock_logger, mock_get_settings):
    # Force logger to raise inside try block
    mock_logger.info.side_effect = Exception("Logging failed")

    mock_settings = MagicMock()
    mock_settings.SMTP_FROM = "noreply@example.com"
    mock_get_settings.return_value = mock_settings

    to = "user@example.com"
    subject = "Failing Subject"
    body = "Body"

    await send_email(to, subject, body)

    mock_logger.error.assert_called_once()
    args, _ = mock_logger.error.call_args
    assert "Failed to send email to" in args[0]
