"""
Auto-generated Pydantic models for Aureon™
Platform: aureon v0.1.0
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OpportunityCreate(BaseModel):
    """A federal contracting opportunity from SAM.gov"""

    notice_id: str
    title: str
    agency: str
    sub_agency: str | None = None
    naics_codes: list[str]
    set_asides: list[str]
    response_deadline: datetime
    estimated_value: Decimal
    place_of_performance: str | None = None
    solicitation_type: str
    full_text: str
    embedding: list[float]
    source_url: str


class Opportunity(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    notice_id: str
    title: str
    agency: str
    sub_agency: str | None = None
    naics_codes: list[str]
    set_asides: list[str]
    response_deadline: datetime
    estimated_value: Decimal
    place_of_performance: str | None = None
    solicitation_type: str
    full_text: str
    embedding: list[float]
    source_url: str

    class Config:
        from_attributes = True


class OpportunityUpdate(BaseModel):
    notice_id: str | None = None
    title: str | None = None
    agency: str | None = None
    sub_agency: str | None = None
    naics_codes: list[str] | None = None
    set_asides: list[str] | None = None
    response_deadline: datetime | None = None
    estimated_value: Decimal | None = None
    place_of_performance: str | None = None
    solicitation_type: str | None = None
    full_text: str | None = None
    embedding: list[float] | None = None
    source_url: str | None = None


class VendorCreate(BaseModel):
    """A potential contractor/vendor"""

    cage_code: str
    uei: str
    legal_name: str
    dba_name: str | None = None
    capabilities: list[str]
    naics_codes: list[str]
    certifications: list[str]
    past_performance_score: float | None = None
    sam_status: str
    contact_email: str
    hubzone_qualified: bool
    capability_embedding: list[float]


class Vendor(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int = 1
    cage_code: str
    uei: str
    legal_name: str
    dba_name: str | None = None
    capabilities: list[str]
    naics_codes: list[str]
    certifications: list[str]
    past_performance_score: float | None = None
    sam_status: str
    contact_email: str
    hubzone_qualified: bool
    capability_embedding: list[float]

    class Config:
        from_attributes = True


class VendorUpdate(BaseModel):
    cage_code: str | None = None
    uei: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    capabilities: list[str] | None = None
    naics_codes: list[str] | None = None
    certifications: list[str] | None = None
    past_performance_score: float | None = None
    sam_status: str | None = None
    contact_email: str | None = None
    hubzone_qualified: bool | None = None
    capability_embedding: list[float] | None = None


class OpportunityMatchCreate(BaseModel):
    """AI-scored match between opportunity and vendor"""

    match_score: float
    capability_score: float
    compliance_score: float
    past_performance_score: float
    set_aside_eligible: bool
    explanation: str
    model_version: str
    confidence: float


class OpportunityMatch(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    match_score: float
    capability_score: float
    compliance_score: float
    past_performance_score: float
    set_aside_eligible: bool
    explanation: str
    model_version: str
    confidence: float

    class Config:
        from_attributes = True


class OpportunityMatchUpdate(BaseModel):
    match_score: float | None = None
    capability_score: float | None = None
    compliance_score: float | None = None
    past_performance_score: float | None = None
    set_aside_eligible: bool | None = None
    explanation: str | None = None
    model_version: str | None = None
    confidence: float | None = None

