"""Regression tests for B-5 (2026-05-04 sign-off).

Lead routing operations (`move_to_jobs`, `move_to_sales`, `mark_contacted`)
were not emitting audit-log entries. The fix adds a best-effort
``_audit_log_lead_routing`` helper that mirrors ``_audit_log_convert_override``
and is wired into each success path. Audit failures must NEVER block the
operation — the helper catches ``Exception`` and only logs.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import LeadSituation
from grins_platform.services.lead_service import LeadService


def _make_lead(
    *,
    lead_id: uuid.UUID | None = None,
    situation: str = LeadSituation.REPAIR.value,
    customer_id: uuid.UUID | None = None,
    assigned_to: uuid.UUID | None = None,
    notes: str | None = None,
) -> MagicMock:
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = "Audit Tester"
    lead.phone = "6125550199"
    lead.email = None
    lead.situation = situation
    lead.notes = notes
    lead.customer_id = customer_id
    lead.moved_to = None
    lead.moved_at = None
    lead.job_requested = None
    lead.sms_consent = False
    lead.assigned_to = assigned_to
    lead.action_tags = []
    lead.contacted_at = None
    return lead


def _build_service(
    *,
    lead_repo=None,
    customer_service=None,
    job_service=None,
) -> LeadService:
    repo = lead_repo or AsyncMock()
    # Cluster A cascade: neutralize session.execute chain so cascade
    # helpers (attachments, tag pre-checks) are no-ops in unit tests.
    _result = MagicMock()
    _result.scalars.return_value.all.return_value = []
    _result.all.return_value = []
    _result.scalar_one_or_none.return_value = None
    repo.session.execute = AsyncMock(return_value=_result)
    return LeadService(
        lead_repository=repo,
        customer_service=customer_service or AsyncMock(),
        job_service=job_service or AsyncMock(),
        staff_repository=AsyncMock(),
    )


@pytest.mark.unit
class TestLeadRoutingAuditLog:
    """B-5 — audit-log emission on every lead-routing success."""

    @pytest.mark.asyncio
    async def test_move_to_jobs_emits_audit_with_actor(self) -> None:
        actor = uuid4()
        customer_id = uuid4()
        lead = _make_lead(customer_id=customer_id)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        job_mock = MagicMock()
        job_mock.id = uuid4()
        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=job_mock)

        service = _build_service(lead_repo=repo, job_service=job_service)

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository"
        ) as repo_cls:
            instance = AsyncMock()
            repo_cls.return_value = instance

            await service.move_to_jobs(lead.id, actor_staff_id=actor)

        # Exactly one routing audit emission for repair (non-estimate).
        actions = [c.kwargs["action"] for c in instance.create.await_args_list]
        assert "lead.move_to_jobs" in actions
        # Actor is propagated.
        for call in instance.create.await_args_list:
            if call.kwargs["action"] == "lead.move_to_jobs":
                assert call.kwargs["actor_id"] == actor
                assert call.kwargs["resource_type"] == "lead"
                assert call.kwargs["resource_id"] == lead.id
                assert call.kwargs["details"]["forced"] is False
                assert call.kwargs["details"]["job_id"] == str(job_mock.id)

    @pytest.mark.asyncio
    async def test_move_to_jobs_force_emits_estimate_override_and_main_audit(
        self,
    ) -> None:
        actor = uuid4()
        # Use EXPLORING which is requires_estimate per the SITUATION_JOB_MAP.
        lead = _make_lead(
            customer_id=uuid4(), situation=LeadSituation.EXPLORING.value
        )
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        job_mock = MagicMock()
        job_mock.id = uuid4()
        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=job_mock)

        service = _build_service(lead_repo=repo, job_service=job_service)

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository"
        ) as repo_cls:
            instance = AsyncMock()
            repo_cls.return_value = instance

            await service.move_to_jobs(
                lead.id, force=True, actor_staff_id=actor
            )

        actions = [c.kwargs["action"] for c in instance.create.await_args_list]
        assert "lead.move_to_jobs.estimate_override" in actions
        assert "lead.move_to_jobs" in actions

    @pytest.mark.asyncio
    async def test_move_to_sales_emits_audit_with_actor(self) -> None:
        actor = uuid4()
        customer_id = uuid4()
        lead = _make_lead(customer_id=customer_id)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()
        repo.session = AsyncMock()

        service = _build_service(lead_repo=repo)

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository"
        ) as repo_cls:
            instance = AsyncMock()
            repo_cls.return_value = instance

            await service.move_to_sales(lead.id, actor_staff_id=actor)

        actions = [c.kwargs["action"] for c in instance.create.await_args_list]
        assert "lead.move_to_sales" in actions
        for call in instance.create.await_args_list:
            if call.kwargs["action"] == "lead.move_to_sales":
                assert call.kwargs["actor_id"] == actor

    @pytest.mark.asyncio
    async def test_mark_contacted_emits_audit_with_actor(self) -> None:
        actor = uuid4()
        lead = _make_lead()
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        service = _build_service(lead_repo=repo)

        with patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository"
        ) as repo_cls:
            instance = AsyncMock()
            repo_cls.return_value = instance
            # mark_contacted re-reads the lead after update; return same mock.
            repo.get_by_id.side_effect = [lead, lead]

            with patch(
                "grins_platform.schemas.lead.LeadResponse.model_validate",
                return_value=MagicMock(),
            ):
                await service.mark_contacted(lead.id, actor_staff_id=actor)

        actions = [c.kwargs["action"] for c in instance.create.await_args_list]
        assert actions == ["lead.contacted"]
        assert instance.create.await_args_list[0].kwargs["actor_id"] == actor
