"""Tests for SMS API endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from grins_platform.database import get_db_session
from grins_platform.main import app
from grins_platform.services.sms_service import SMSConsentDeniedError


def _mock_customer(customer_id=None):
    """Create a mock Customer for endpoint tests."""
    c = Mock()
    c.id = customer_id or uuid4()
    c.phone = "+16125551234"
    c.first_name = "Test"
    c.last_name = "User"
    return c


def _mock_db_with_customer(customer):
    """Create a mock async DB session that returns the given customer."""
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = customer
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


@pytest.mark.asyncio
class TestSMSSendEndpoint:
    """Tests for /api/v1/sms/send endpoint."""

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_send_returns_success(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that send returns success response."""
        mock_sms = mock_sms_cls.return_value
        message_id = uuid4()
        customer_id = uuid4()
        mock_sms.send_message = AsyncMock(
            return_value={
                "success": True,
                "message_id": str(message_id),
                "provider_message_id": "SM123",
                "status": "sent",
            },
        )

        mock_customer = _mock_customer(customer_id)
        mock_db = _mock_db_with_customer(mock_customer)

        app.dependency_overrides[get_db_session] = lambda: mock_db
        try:
            response = await client.post(
                "/api/v1/sms/send",
                json={
                    "customer_id": str(customer_id),
                    "phone": "6125551234",
                    "message": "Test message",
                    "message_type": "appointment_confirmation",
                    "sms_opt_in": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        finally:
            app.dependency_overrides.pop(get_db_session, None)

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_send_enforces_consent(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that send enforces SMS consent."""
        mock_sms = mock_sms_cls.return_value
        customer_id = uuid4()
        mock_sms.send_message = AsyncMock(
            side_effect=SMSConsentDeniedError("Consent denied"),
        )

        mock_customer = _mock_customer(customer_id)
        mock_db = _mock_db_with_customer(mock_customer)

        app.dependency_overrides[get_db_session] = lambda: mock_db
        try:
            response = await client.post(
                "/api/v1/sms/send",
                json={
                    "customer_id": str(customer_id),
                    "phone": "6125551234",
                    "message": "Test message",
                    "message_type": "appointment_confirmation",
                    "sms_opt_in": False,
                },
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db_session, None)

    async def test_send_requires_phone(self, client: AsyncClient) -> None:
        """Test that send requires phone number."""
        response = await client.post(
            "/api/v1/sms/send",
            json={
                "customer_id": str(uuid4()),
                "message": "Test message",
                "message_type": "appointment_confirmation",
                "sms_opt_in": True,
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestSMSWebhookEndpoint:
    """Tests for /api/v1/sms/webhook endpoint."""

    @patch("grins_platform.api.v1.sms.validate_twilio_signature", return_value=True)
    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_webhook_processes_incoming(
        self,
        mock_sms_cls: Mock,
        _mock_validate: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that webhook processes incoming messages."""
        mock_sms = mock_sms_cls.return_value
        mock_sms.handle_webhook = AsyncMock(
            return_value={
                "action": "received",
                "phone": "6125551234",
                "message": "Test reply",
            },
        )

        response = await client.post(
            "/api/v1/sms/webhook",
            data={
                "From": "+16125551234",
                "Body": "Test reply",
                "MessageSid": "SM123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "received"


@pytest.mark.asyncio
class TestCommunicationsQueueEndpoint:
    """Tests for /api/v1/communications/queue endpoint."""

    @patch("grins_platform.api.v1.sms.SentMessageRepository")
    async def test_queue_returns_pending_messages(
        self,
        mock_repo_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that queue returns pending messages."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_queue = AsyncMock(return_value=([], 0))

        response = await client.get("/api/v1/communications/queue")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @patch("grins_platform.api.v1.sms.SentMessageRepository")
    async def test_queue_filters_by_status(
        self,
        mock_repo_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that queue filters by status."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_queue = AsyncMock(return_value=([], 0))

        response = await client.get(
            "/api/v1/communications/queue",
            params={"status_filter": "pending"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestBulkSendEndpoint:
    """Tests for /api/v1/communications/send-bulk endpoint."""

    @patch("grins_platform.api.v1.sms.CampaignRepository")
    async def test_bulk_send_processes_messages(
        self,
        mock_repo_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that bulk send enqueues recipients and returns 202."""
        campaign_id = uuid4()
        mock_repo = mock_repo_cls.return_value
        mock_repo.create = AsyncMock(
            return_value=Mock(id=campaign_id),
        )
        mock_repo.add_recipients_bulk = AsyncMock(return_value=[])

        response = await client.post(
            "/api/v1/communications/send-bulk",
            json={
                "message": "Test bulk message",
                "message_type": "appointment_reminder",
                "recipients": [
                    {
                        "customer_id": str(uuid4()),
                        "phone": "6125551234",
                        "sms_opt_in": True,
                    },
                    {
                        "customer_id": str(uuid4()),
                        "phone": "6125555678",
                        "sms_opt_in": True,
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["campaign_id"] == str(campaign_id)
        assert data["total_recipients"] == 2
        assert data["status"] == "pending"

        # Verify campaign was created with correct params
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["campaign_type"] == "SMS"
        assert call_kwargs["status"] == "sending"
        assert call_kwargs["body"] == "Test bulk message"

        # Verify recipients were enqueued
        mock_repo.add_recipients_bulk.assert_called_once()
        recipients_arg = mock_repo.add_recipients_bulk.call_args[0][0]
        assert len(recipients_arg) == 2
        assert all(r["delivery_status"] == "pending" for r in recipients_arg)
        assert all(r["channel"] == "sms" for r in recipients_arg)


@pytest.mark.asyncio
class TestDeleteMessageEndpoint:
    """Tests for /api/v1/communications/{id} endpoint."""

    @patch("grins_platform.api.v1.sms.SentMessageRepository")
    async def test_delete_removes_message(
        self,
        mock_repo_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that delete removes message from queue."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.delete = AsyncMock(return_value=True)

        message_id = uuid4()
        response = await client.delete(f"/api/v1/communications/{message_id}")
        assert response.status_code == 200

    @patch("grins_platform.api.v1.sms.SentMessageRepository")
    async def test_delete_returns_404_for_missing(
        self,
        mock_repo_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that delete returns 404 for missing message."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.delete = AsyncMock(return_value=False)

        message_id = uuid4()
        response = await client.delete(f"/api/v1/communications/{message_id}")
        assert response.status_code == 404


@pytest.mark.property
@pytest.mark.asyncio
class TestSMSConsentProperty:
    """Property test: SMS consent enforcement."""

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_consent_required_for_all_message_types(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Property 13: SMS consent required for all message types."""
        mock_sms = mock_sms_cls.return_value
        mock_sms.send_message = AsyncMock(
            side_effect=SMSConsentDeniedError("Consent denied"),
        )

        customer_id = uuid4()
        mock_customer = _mock_customer(customer_id)
        mock_db = _mock_db_with_customer(mock_customer)

        message_types = [
            "appointment_confirmation",
            "appointment_reminder",
            "on_the_way",
            "arrival",
            "completion",
            "invoice",
            "payment_reminder",
        ]

        app.dependency_overrides[get_db_session] = lambda: mock_db
        try:
            for message_type in message_types:
                response = await client.post(
                    "/api/v1/sms/send",
                    json={
                        "customer_id": str(customer_id),
                        "phone": "6125551234",
                        "message": "Test message",
                        "message_type": message_type,
                        "sms_opt_in": False,
                    },
                )
                assert response.status_code == 403, (
                    f"Expected 403 for {message_type}, got {response.status_code}"
                )
        finally:
            app.dependency_overrides.pop(get_db_session, None)
