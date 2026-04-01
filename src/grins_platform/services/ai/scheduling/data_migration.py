"""
Data migration and onboarding utilities for the scheduling engine.

Provides import, cleaning, enrichment, and quality-checking tools
for customer, job, resource, and schedule data from external systems.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Minimum data requirements per AI capability tier
_TIER_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "basic": {
        "description": "Basic scheduling — manual assignment with AI suggestions",
        "min_customers": 10,
        "min_jobs": 20,
        "min_resources": 2,
        "min_schedule_history_days": 0,
        "required_fields": ["customer_name", "job_type", "resource_name"],
    },
    "standard": {
        "description": "Standard AI scheduling — auto-build with 15 criteria",
        "min_customers": 50,
        "min_jobs": 100,
        "min_resources": 3,
        "min_schedule_history_days": 30,
        "required_fields": [
            "customer_name",
            "customer_address",
            "job_type",
            "job_duration",
            "resource_name",
            "resource_skills",
        ],
    },
    "advanced": {
        "description": "Full 30-criteria AI with predictive intelligence",
        "min_customers": 200,
        "min_jobs": 500,
        "min_resources": 5,
        "min_schedule_history_days": 90,
        "required_fields": [
            "customer_name",
            "customer_address",
            "customer_lat_lon",
            "job_type",
            "job_duration",
            "job_revenue",
            "resource_name",
            "resource_skills",
            "resource_certifications",
            "resource_equipment",
            "schedule_history",
        ],
    },
}


class DataMigrationService(LoggerMixin):
    """Data migration and onboarding utilities.

    Provides tools for importing, cleaning, enriching, and validating
    data from external systems to bootstrap the AI scheduling engine.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the data migration service.

        Args:
            session: Async database session for persistence.
        """
        super().__init__()
        self._session = session

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    async def import_data(
        self,
        data_type: str,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Import customer, job, resource, or schedule data.

        Args:
            data_type: One of ``customer``, ``job``, ``resource``,
                ``schedule``.
            records: List of record dicts to import.

        Returns:
            Summary dict with ``imported``, ``skipped``, ``errors``
            counts and ``details`` list.
        """
        self.log_started("import_data", data_type=data_type, count=len(records))

        try:
            cleaned = await self.clean_data(data_type, records)
            quality_issues = await self.flag_quality_issues(cleaned)

            imported = len(cleaned)
            skipped = len(records) - imported
            errors_found = len(quality_issues)

            # Stub: actual DB persistence would happen here
            self.log_completed(
                "import_data",
                data_type=data_type,
                imported=imported,
                skipped=skipped,
                quality_issues=errors_found,
            )

            return {
                "data_type": data_type,
                "total_records": len(records),
                "imported": imported,
                "skipped": skipped,
                "errors": errors_found,
                "quality_issues": quality_issues,
            }

        except Exception as exc:
            self.log_failed("import_data", error=exc, data_type=data_type)
            return {
                "data_type": data_type,
                "total_records": len(records),
                "imported": 0,
                "skipped": len(records),
                "errors": 1,
                "quality_issues": [{"error": str(exc)}],
            }

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    async def clean_data(
        self,
        data_type: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Clean and standardise imported records.

        Performs geocoding of addresses, standardisation of job types,
        and mapping of skill tags to the platform's taxonomy.

        Args:
            data_type: Record type (``customer``, ``job``, etc.).
            records: Raw records to clean.

        Returns:
            List of cleaned record dicts.
        """
        self.log_started("clean_data", data_type=data_type, count=len(records))

        cleaned: list[dict[str, Any]] = []
        for record in records:
            clean_record = dict(record)

            # Standardise job types
            if data_type == "job" and "job_type" in clean_record:
                clean_record["job_type"] = (
                    clean_record["job_type"].strip().lower().replace(" ", "_")
                )

            # Standardise skill tags
            if data_type == "resource" and "skills" in clean_record:
                raw_skills = clean_record.get("skills", [])
                if isinstance(raw_skills, str):
                    raw_skills = [s.strip() for s in raw_skills.split(",")]
                clean_record["skills"] = [
                    s.strip().lower().replace(" ", "_") for s in raw_skills
                ]

            # Stub: geocode addresses (would call Google Maps Geocoding)
            if "address" in clean_record and "latitude" not in clean_record:
                clean_record["latitude"] = None
                clean_record["longitude"] = None
                clean_record["geocode_status"] = "pending"

            cleaned.append(clean_record)

        self.log_completed("clean_data", data_type=data_type, cleaned=len(cleaned))
        return cleaned

    # ------------------------------------------------------------------
    # Minimum requirements check
    # ------------------------------------------------------------------

    async def check_minimum_requirements(self) -> dict[str, Any]:
        """Check minimum data requirements per AI capability tier.

        Returns:
            Dict with ``tier`` (highest qualifying tier), per-tier
            status, and ``missing`` fields for the next tier up.
        """
        self.log_started("check_minimum_requirements")

        # Stub: would query actual DB counts
        current_counts: dict[str, int] = {
            "customers": 0,
            "jobs": 0,
            "resources": 0,
            "schedule_history_days": 0,
        }

        result: dict[str, Any] = {
            "current_counts": current_counts,
            "qualifying_tier": "none",
            "tier_status": {},
        }

        for tier_name, reqs in _TIER_REQUIREMENTS.items():
            meets = (
                current_counts["customers"] >= reqs["min_customers"]
                and current_counts["jobs"] >= reqs["min_jobs"]
                and current_counts["resources"] >= reqs["min_resources"]
                and current_counts["schedule_history_days"]
                >= reqs["min_schedule_history_days"]
            )
            result["tier_status"][tier_name] = {
                "meets_requirements": meets,
                "description": reqs["description"],
                "required_fields": reqs["required_fields"],
            }
            if meets:
                result["qualifying_tier"] = tier_name

        self.log_completed(
            "check_minimum_requirements",
            qualifying_tier=result["qualifying_tier"],
        )
        return result

    # ------------------------------------------------------------------
    # Quality flagging
    # ------------------------------------------------------------------

    async def flag_quality_issues(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Flag data quality issues with guided remediation.

        Args:
            records: Cleaned records to validate.

        Returns:
            List of issue dicts with ``field``, ``issue``,
            ``severity``, and ``remediation`` guidance.
        """
        self.log_started("flag_quality_issues", count=len(records))

        issues: list[dict[str, Any]] = []
        for idx, record in enumerate(records):
            # Missing address
            if not record.get("address"):
                issues.append({
                    "record_index": idx,
                    "field": "address",
                    "issue": "missing_address",
                    "severity": "warning",
                    "remediation": "Add a street address to enable geographic routing.",
                })

            # Missing geocode
            if record.get("geocode_status") == "pending":
                issues.append({
                    "record_index": idx,
                    "field": "latitude/longitude",
                    "issue": "geocode_pending",
                    "severity": "info",
                    "remediation": (
                        "Address will be geocoded automatically. "
                        "Verify coordinates after import."
                    ),
                })

            # Missing skills for resources
            if not record.get("skills") and record.get("resource_name"):
                issues.append({
                    "record_index": idx,
                    "field": "skills",
                    "issue": "missing_skills",
                    "severity": "warning",
                    "remediation": (
                        "Add skill tags so the AI can match resources to jobs."
                    ),
                })

        self.log_completed("flag_quality_issues", issues_found=len(issues))
        return issues

    # ------------------------------------------------------------------
    # Enrichment
    # ------------------------------------------------------------------

    async def enrich_data(
        self,
        data_type: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Incrementally enrich records for ML accuracy.

        Adds derived fields such as CLV scores, predicted complexity,
        and performance metrics based on historical data.

        Args:
            data_type: Record type (``customer``, ``job``, etc.).
            records: Records to enrich.

        Returns:
            Enriched record dicts.
        """
        self.log_started("enrich_data", data_type=data_type, count=len(records))

        enriched: list[dict[str, Any]] = []
        for record in records:
            enriched_record = dict(record)

            if data_type == "customer":
                # Stub: calculate CLV from historical revenue
                enriched_record.setdefault("clv_score", 0.0)
                enriched_record.setdefault("preferred_resource_id", None)

            elif data_type == "job":
                # Stub: predict complexity from historical patterns
                enriched_record.setdefault("predicted_complexity", 1.0)
                enriched_record.setdefault("revenue_per_hour", None)

            elif data_type == "resource":
                # Stub: calculate performance metrics
                enriched_record.setdefault("performance_score", None)
                enriched_record.setdefault("callback_rate", None)
                enriched_record.setdefault("avg_satisfaction", None)

            enriched.append(enriched_record)

        self.log_completed("enrich_data", data_type=data_type, enriched=len(enriched))
        return enriched
