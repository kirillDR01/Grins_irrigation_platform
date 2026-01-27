"""Tests for SMS API endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from grins_platform.services.sms_service import SMSOptInError


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
        mock_sms.send_message = AsyncMock(
            return_value={
                "success": True,
                "message_id": str(message_id),
                "twilio_sid": "SM123",
                "status": "sent",
            },
        )

        response = await client.post(
            "/api/v1/sms/send",
            json={
                "customer_id": str(uuid4()),
                "phone": "6125551234",
                "message": "Test message",
                "message_type": "appointment_confirmation",
                "sms_opt_in": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_send_enforces_opt_in(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that send enforces SMS opt-in."""
        mock_sms = mock_sms_cls.return_value
        mock_sms.send_message = AsyncMock(
            side_effect=SMSOptInError("Customer has not opted in to SMS"),
        )

        response = await client.post(
            "/api/v1/sms/send",
            json={
                "customer_id": str(uuid4()),
                "phone": "6125551234",
                "message": "Test message",
                "message_type": "appointment_confirmation",
                "sms_opt_in": False,
            },
        )
        assert response.status_code == 403

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

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_bulk_send_processes_messages(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that bulk send processes multiple messages."""
        mock_sms = mock_sms_cls.return_value
        mock_sms.send_message = AsyncMock(
            return_value={
                "success": True,
                "message_id": str(uuid4()),
                "status": "sent",
            },
        )

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
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["success_count"] == 2


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
class TestSMSOptInProperty:
    """Property test: SMS opt-in enforcement."""

    @patch("grins_platform.api.v1.sms.SMSService")
    async def test_opt_in_required_for_all_message_types(
        self,
        mock_sms_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Property 13: SMS opt-in required for all message types."""
        mock_sms = mock_sms_cls.return_value
        mock_sms.send_message = AsyncMock(
            side_effect=SMSOptInError("Customer has not opted in to SMS"),
        )

        message_types = [
            "appointment_confirmation",
            "appointment_reminder",
            "on_the_way",
            "arrival",
            "completion",
            "invoice",
            "payment_reminder",
        ]

        for message_type in message_types:
            response = await client.post(
                "/api/v1/sms/send",
                json={
                    "customer_id": str(uuid4()),
                    "phone": "6125551234",
                    "message": "Test message",
                    "message_type": message_type,
                    "sms_opt_in": False,
                },
            )
            # All should be rejected due to opt-in
            assert response.status_code == 403
