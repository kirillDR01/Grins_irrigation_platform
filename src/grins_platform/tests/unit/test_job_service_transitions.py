"""Unit tests for JobService.VALID_TRANSITIONS edges added in Sprint 4.

Validates: bughunt M-1, E-BUG-G
"""

from __future__ import annotations

import pytest

from grins_platform.models.enums import JobStatus
from grins_platform.services.job_service import JobService


@pytest.mark.unit
class TestValidTransitionsIncludeSkipToCompleted:
    """M-1: TO_BE_SCHEDULED and SCHEDULED should both allow direct
    completion to support service-agreement flows and admin
    force-complete (bughunt M-1, E-BUG-G).
    """

    def test_tb_scheduled_can_transition_to_completed(self) -> None:
        valid = JobService.VALID_TRANSITIONS[JobStatus.TO_BE_SCHEDULED]
        assert JobStatus.COMPLETED in valid

    def test_scheduled_can_transition_to_completed(self) -> None:
        valid = JobService.VALID_TRANSITIONS[JobStatus.SCHEDULED]
        assert JobStatus.COMPLETED in valid

    def test_in_progress_still_transitions_to_completed(self) -> None:
        valid = JobService.VALID_TRANSITIONS[JobStatus.IN_PROGRESS]
        assert JobStatus.COMPLETED in valid

    def test_terminal_states_remain_terminal(self) -> None:
        assert JobService.VALID_TRANSITIONS[JobStatus.COMPLETED] == set()
        assert JobService.VALID_TRANSITIONS[JobStatus.CANCELLED] == set()
