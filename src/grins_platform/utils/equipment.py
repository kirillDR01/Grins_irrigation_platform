"""
Equipment matching utilities for route optimization.

This module provides utility functions for matching staff equipment
to job requirements.

Validates: Requirements 2.2, 2.4 (Route Optimization)
"""

from __future__ import annotations

from typing import Protocol


class HasEquipment(Protocol):
    """Protocol for objects with assigned_equipment attribute."""

    assigned_equipment: list[str] | None


class HasEquipmentRequired(Protocol):
    """Protocol for objects with equipment_required attribute."""

    equipment_required: list[str] | None


def can_staff_handle_job(staff: HasEquipment, job: HasEquipmentRequired) -> bool:
    """Check if a staff member has all required equipment for a job.

    Args:
        staff: Staff member to check (must have assigned_equipment attribute)
        job: Job with equipment requirements (must have equipment_required attribute)

    Returns:
        True if staff has all required equipment, False otherwise

    Validates: Requirements 2.2, 2.4
    """
    # Get job's required equipment
    required_equipment = job.equipment_required

    # If no equipment required, any staff can handle it
    if not required_equipment:
        return True

    # Get staff's assigned equipment
    staff_equipment = staff.assigned_equipment or []

    # Check if staff has ALL required equipment
    return all(equip in staff_equipment for equip in required_equipment)


def get_missing_equipment(staff: HasEquipment, job: HasEquipmentRequired) -> list[str]:
    """Get list of equipment the staff member is missing for a job.

    Args:
        staff: Staff member to check
        job: Job with equipment requirements

    Returns:
        List of missing equipment items (empty if staff can handle job)
    """
    required_equipment = job.equipment_required

    if not required_equipment:
        return []

    staff_equipment = set(staff.assigned_equipment or [])
    return [equip for equip in required_equipment if equip not in staff_equipment]
