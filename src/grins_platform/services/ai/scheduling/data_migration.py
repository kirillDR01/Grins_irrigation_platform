"""
Data migration and onboarding utilities for AI scheduling.

Provides tools for importing, cleaning, and validating data from
external systems to enable AI scheduling capabilities.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

from __future__ import annotations

import re
from typing import Any

from grins_platform.log_config import LoggerMixin

# Minimum data requirements per AI capability tier
_CAPABILITY_TIERS: dict[str, dict[str, int]] = {
    "basic_scheduling": {
        "min_customers": 1,
        "min_staff": 1,
        "min_jobs": 0,
        "min_service_offerings": 1,
    },
    "criteria_scoring": {
        "min_customers": 10,
        "min_staff": 2,
        "min_jobs": 5,
        "min_service_offerings": 3,
    },
    "predictive_scheduling": {
        "min_customers": 50,
        "min_staff": 3,
        "min_jobs": 100,
        "min_service_offerings": 5,
    },
    "ml_complexity_prediction": {
        "min_customers": 100,
        "min_staff": 5,
        "min_jobs": 500,
        "min_service_offerings": 5,
    },
}

# Standard job type mappings for normalization
_JOB_TYPE_MAP: dict[str, str] = {
    "spring opening": "Spring Opening",
    "spring open": "Spring Opening",
    "startup": "Spring Opening",
    "fall closing": "Fall Closing",
    "fall close": "Fall Closing",
    "winterize": "Fall Closing",
    "winterization": "Fall Closing",
    "maintenance": "Maintenance",
    "maint": "Maintenance",
    "repair": "Repair",
    "fix": "Repair",
    "installation": "Installation",
    "install": "Installation",
    "new install": "Installation",
    "diagnostic": "Diagnostic",
    "diag": "Diagnostic",
    "estimate": "Estimate",
    "quote": "Estimate",
    "backflow": "Backflow Test",
    "backflow test": "Backflow Test",
}

# Standard skill tag mappings
_SKILL_TAG_MAP: dict[str, str] = {
    "backflow": "backflow_certified",
    "backflow testing": "backflow_certified",
    "backflow certification": "backflow_certified",
    "drip": "drip_irrigation",
    "drip irrigation": "drip_irrigation",
    "smart controller": "smart_controller",
    "wifi controller": "smart_controller",
    "commercial": "commercial_systems",
    "large commercial": "commercial_systems",
}


class DataMigrationService(LoggerMixin):
    """Data migration and onboarding utilities for AI scheduling.

    Provides import, cleaning, validation, and quality-flagging tools
    to prepare data for AI scheduling capabilities.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(self) -> None:
        """Initialise the data migration service."""
        super().__init__()

    def import_customers(
        self,
        raw_records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Import and clean customer records from external systems.

        Args:
            raw_records: Raw customer records from external system.

        Returns:
            Tuple of (cleaned_records, error_records).
        """
        self.log_started("import_customers", record_count=len(raw_records))
        cleaned: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for i, record in enumerate(raw_records):
            try:
                cleaned_record = self._clean_customer(record)
                cleaned.append(cleaned_record)
            except Exception as exc:  # noqa: PERF203
                errors.append({"index": i, "record": record, "error": str(exc)})

        self.log_completed(
            "import_customers",
            cleaned_count=len(cleaned),
            error_count=len(errors),
        )
        return cleaned, errors

    def import_jobs(
        self,
        raw_records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Import and clean job records from external systems.

        Args:
            raw_records: Raw job records.

        Returns:
            Tuple of (cleaned_records, error_records).
        """
        self.log_started("import_jobs", record_count=len(raw_records))
        cleaned: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for i, record in enumerate(raw_records):
            try:
                cleaned_record = self._clean_job(record)
                cleaned.append(cleaned_record)
            except Exception as exc:  # noqa: PERF203
                errors.append({"index": i, "record": record, "error": str(exc)})

        self.log_completed(
            "import_jobs",
            cleaned_count=len(cleaned),
            error_count=len(errors),
        )
        return cleaned, errors

    def check_capability_tier(
        self,
        data_counts: dict[str, int],
    ) -> dict[str, bool]:
        """Check which AI capability tiers are available given data counts.

        Args:
            data_counts: Dict with keys: customers, staff, jobs, service_offerings.

        Returns:
            Dict mapping tier name to availability bool.
        """
        self.log_started("check_capability_tier")
        results: dict[str, bool] = {}

        for tier, requirements in _CAPABILITY_TIERS.items():
            available = all(
                data_counts.get(key.replace("min_", ""), 0) >= min_val
                for key, min_val in requirements.items()
            )
            results[tier] = available

        self.log_completed("check_capability_tier", tiers=results)
        return results

    def flag_data_quality_issues(
        self,
        records: list[dict[str, Any]],
        record_type: str,
    ) -> list[dict[str, Any]]:
        """Flag data quality issues in records.

        Args:
            records: Records to check.
            record_type: Type of record (customer, job, staff, property).

        Returns:
            List of quality issue dicts with record index and issues.
        """
        self.log_started(
            "flag_data_quality_issues",
            record_type=record_type,
            record_count=len(records),
        )
        issues: list[dict[str, Any]] = []

        for i, record in enumerate(records):
            record_issues: list[str] = []

            if record_type == "customer":
                if not record.get("phone") and not record.get("email"):
                    record_issues.append("Missing contact info (phone or email)")
                if not record.get("address"):
                    record_issues.append("Missing address")

            elif record_type == "job":
                if not record.get("job_type"):
                    record_issues.append("Missing job type")
                if not record.get("customer_id"):
                    record_issues.append("Missing customer reference")

            elif record_type == "staff":
                if not record.get("skills"):
                    record_issues.append("No skills/certifications listed")
                if not record.get("availability"):
                    record_issues.append("No availability windows defined")

            elif record_type == "property":
                if not record.get("latitude") or not record.get("longitude"):
                    record_issues.append("Missing GPS coordinates (needed for routing)")

            if record_issues:
                issues.append(
                    {
                        "index": i,
                        "record_id": record.get("id"),
                        "issues": record_issues,
                        "remediation": self._suggest_remediation(
                            record_type, record_issues
                        ),
                    }
                )

        self.log_completed(
            "flag_data_quality_issues",
            record_type=record_type,
            issue_count=len(issues),
        )
        return issues

    def enrich_record(
        self,
        record: dict[str, Any],
        record_type: str,
    ) -> dict[str, Any]:
        """Incrementally enrich a record for ML model accuracy.

        Args:
            record: Record to enrich.
            record_type: Type of record.

        Returns:
            Enriched record dict.
        """
        enriched = dict(record)

        if record_type == "job":
            # Normalize job type
            raw_type = str(enriched.get("job_type", "")).lower().strip()
            enriched["job_type"] = _JOB_TYPE_MAP.get(raw_type, enriched.get("job_type"))

            # Map skill tags
            skills = enriched.get("required_skills", [])
            enriched["required_skills"] = [
                _SKILL_TAG_MAP.get(s.lower(), s) for s in skills
            ]

        elif record_type == "staff":
            skills = enriched.get("skills", [])
            enriched["skills"] = [_SKILL_TAG_MAP.get(s.lower(), s) for s in skills]

        return enriched

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_customer(record: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize a customer record."""
        cleaned = dict(record)

        # Normalize phone number
        phone = str(cleaned.get("phone", "")).strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            cleaned["phone"] = f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            cleaned["phone"] = f"+{digits}"

        # Normalize email
        email = str(cleaned.get("email", "")).strip().lower()
        if email:
            cleaned["email"] = email

        # Normalize name
        for field in ("first_name", "last_name"):
            val = str(cleaned.get(field, "")).strip().title()
            if val:
                cleaned[field] = val

        return cleaned

    @staticmethod
    def _clean_job(record: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize a job record."""
        cleaned = dict(record)

        # Normalize job type
        raw_type = str(cleaned.get("job_type", "")).lower().strip()
        cleaned["job_type"] = _JOB_TYPE_MAP.get(raw_type, cleaned.get("job_type"))

        # Normalize priority (1-5)
        priority = cleaned.get("priority", 3)
        try:
            cleaned["priority"] = max(1, min(5, int(priority)))
        except (TypeError, ValueError):
            cleaned["priority"] = 3

        return cleaned

    @staticmethod
    def _suggest_remediation(
        record_type: str,
        issues: list[str],
    ) -> list[str]:
        """Suggest remediation steps for data quality issues."""
        remediations: list[str] = []
        for issue in issues:
            if "GPS" in issue or "coordinates" in issue:
                remediations.append(
                    "Geocode the property address using Google Maps API"
                )
            elif "contact" in issue.lower():
                remediations.append("Contact customer to obtain phone number or email")
            elif "skills" in issue.lower():
                remediations.append(
                    "Update staff profile with certifications and skill tags"
                )
            elif "availability" in issue.lower():
                remediations.append(
                    "Define staff availability windows in the Staff module"
                )
            else:
                remediations.append(f"Review and update {record_type} record")
        return remediations
