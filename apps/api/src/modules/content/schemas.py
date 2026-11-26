"""Pydantic schemas for Content Rights Governance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SourceCategory = Literal[
    "original_platform",
    "official_link",
    "licensed_partner",
    "ai_generated",
    "teacher_created",
    "student_created",
    "quarantined_third_party",
]

LegalReviewStatus = Literal["pending", "approved", "rejected", "quarantined"]


class ContentSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    owner_name: str = Field(min_length=2, max_length=160)
    source_category: SourceCategory
    official_url: str | None = Field(default=None, max_length=512)


class ContentSourceResponse(BaseModel):
    id: UUID
    name: str
    owner_name: str
    source_category: str
    official_url: str | None
    created_at: datetime


class ContentLicenseCreate(BaseModel):
    source_id: UUID
    license_name: str = Field(min_length=2, max_length=160)
    commercial_use_allowed: bool = False
    distribution_allowed: bool = False
    hosting_allowed: bool = False
    embedding_allowed: bool = False
    attribution_required: bool = False
    attribution_text: str | None = Field(default=None, max_length=512)
    territory: str = Field(default="IN", max_length=64)
    expires_at: datetime | None = None


class ContentLicenseReview(BaseModel):
    legal_review_status: LegalReviewStatus


class ContentLicenseResponse(BaseModel):
    id: UUID
    source_id: UUID
    license_name: str
    commercial_use_allowed: bool
    distribution_allowed: bool
    hosting_allowed: bool
    embedding_allowed: bool
    attribution_required: bool
    attribution_text: str | None
    territory: str
    expires_at: datetime | None
    legal_review_status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
