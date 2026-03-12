"""Regression test: every DateTime column across all models must use timezone=True.

Prevents BUG #15 from recurring — asyncpg rejects timezone-aware datetimes
when the SQLAlchemy column type is DateTime(timezone=False).
"""

import pytest
from sqlalchemy import DateTime

from grins_platform.models.agreement_status_log import AgreementStatusLog
from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.job import Job
from grins_platform.models.job_status_history import JobStatusHistory
from grins_platform.models.lead import Lead
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.service_agreement_tier import ServiceAgreementTier
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability

ALL_MODELS = [
    Job,
    Appointment,
    Staff,
    ServiceOffering,
    StaffAvailability,
    AgreementStatusLog,
    ServiceAgreementTier,
    JobStatusHistory,
    Customer,
    Lead,
    ServiceAgreement,
]


def _datetime_columns(model: type) -> list[tuple[str, bool]]:
    """Return (column_name, timezone_flag) for every DateTime column in model."""
    results = []
    for col in model.__table__.columns:
        if isinstance(col.type, DateTime):
            results.append((col.name, col.type.timezone))
    return results


@pytest.mark.unit
@pytest.mark.parametrize(
    "model",
    ALL_MODELS,
    ids=lambda m: m.__name__,
)
def test_all_datetime_columns_have_timezone_true(model: type) -> None:
    """Every DateTime column must declare timezone=True."""
    dt_cols = _datetime_columns(model)
    assert dt_cols, (
        f"{model.__name__} has no DateTime columns — check if this is expected"
    )

    missing = [name for name, tz in dt_cols if not tz]
    assert not missing, (
        f"{model.__name__} has DateTime columns without timezone=True: {missing}"
    )
