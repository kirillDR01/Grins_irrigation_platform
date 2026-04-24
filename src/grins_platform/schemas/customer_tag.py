"""Pydantic schemas for customer tags.

Validates: Requirement 12.7
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TagTone(str, Enum):
    neutral = "neutral"
    blue = "blue"
    green = "green"
    amber = "amber"
    violet = "violet"


class TagSource(str, Enum):
    manual = "manual"
    system = "system"


class CustomerTagResponse(BaseModel):
    id: UUID
    customer_id: UUID
    label: str
    tone: TagTone
    source: TagSource
    created_at: datetime

    model_config = {"from_attributes": True}


class TagInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=32)
    tone: TagTone = TagTone.neutral


class CustomerTagsUpdateRequest(BaseModel):
    tags: list[TagInput] = Field(..., max_length=50)

    @field_validator("tags")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def no_duplicate_labels(cls, tags: list[TagInput]) -> list[TagInput]:
        labels = [t.label for t in tags]
        if len(labels) != len(set(labels)):
            msg = "Duplicate tag labels are not allowed within a single request"
            raise ValueError(msg)
        return tags


class CustomerTagsUpdateResponse(BaseModel):
    tags: list[CustomerTagResponse]
