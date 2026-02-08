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
    """A procurement opportunity from SAM.gov, FPDS, or other sources"""

    notice_id: str = Field(..., description="SAM.gov notice ID")
    title: str
    description: str
    agency: str
    office: str
    naics_codes: list[str]
    set_asides: list[str] = Field(..., description="8a, HUBZone, SDVOSB, WOSB, etc.")
    response_deadline: datetime
    posted_date: datetime
    estimated_value: Decimal
    place_of_performance: str
    solicitation_type: str = Field(..., description="RFP, RFI, RFQ, Sources Sought, etc.")
    classification_code: str
    source_url: str
    raw_text: str
    embedding: list[float]
    ai_summary: str
    ai_score: float = Field(..., description="Forge-computed relevance score 0-1")


class Opportunity(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int = 1
    notice_id: str
    title: str
    description: str
    agency: str
    office: str
    naics_codes: list[str]
    set_asides: list[str]
    response_deadline: datetime
    posted_date: datetime
    estimated_value: Decimal
    place_of_performance: str
    solicitation_type: str
    classification_code: str
    source_url: str
    raw_text: str
    embedding: list[float]
    ai_summary: str
    ai_score: float

    class Config:
        from_attributes = True


class OpportunityUpdate(BaseModel):
    notice_id: str | None = None
    title: str | None = None
    description: str | None = None
    agency: str | None = None
    office: str | None = None
    naics_codes: list[str] | None = None
    set_asides: list[str] | None = None
    response_deadline: datetime | None = None
    posted_date: datetime | None = None
    estimated_value: Decimal | None = None
    place_of_performance: str | None = None
    solicitation_type: str | None = None
    classification_code: str | None = None
    source_url: str | None = None
    raw_text: str | None = None
    embedding: list[float] | None = None
    ai_summary: str | None = None
    ai_score: float | None = None


class VendorCreate(BaseModel):
    """A government contractor / vendor"""

    cage_code: str = Field(..., description="Commercial and Government Entity Code")
    uei: str = Field(..., description="Unique Entity Identifier (replaced DUNS)")
    legal_name: str
    dba_name: str
    capabilities: list[str]
    naics_codes: list[str]
    certifications: list[str] = Field(..., description="8a, HUBZone, SDVOSB, WOSB, etc.")
    past_performance_score: float
    size_standard: str = Field(..., description="Small, Other Than Small")
    state: str
    congressional_district: str
    capabilities_statement_url: str
    capabilities_embedding: list[float]
    contact_email: str
    contact_phone: str


class Vendor(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    cage_code: str
    uei: str
    legal_name: str
    dba_name: str
    capabilities: list[str]
    naics_codes: list[str]
    certifications: list[str]
    past_performance_score: float
    size_standard: str
    state: str
    congressional_district: str
    capabilities_statement_url: str
    capabilities_embedding: list[float]
    contact_email: str
    contact_phone: str

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
    size_standard: str | None = None
    state: str | None = None
    congressional_district: str | None = None
    capabilities_statement_url: str | None = None
    capabilities_embedding: list[float] | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class OpportunityMatchCreate(BaseModel):
    """AI-scored match between an opportunity and a vendor"""

    opportunity_id: UUID
    vendor_id: UUID
    match_score: float = Field(..., description="0-1 composite score")
    naics_overlap: float
    certification_match: bool
    capability_similarity: float
    past_performance_weight: float
    geographic_fit: float
    explanation: str = Field(..., description="AI-generated human-readable explanation")
    factors: dict[str, Any] = Field(..., description="Detailed scoring breakdown")


class OpportunityMatch(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    opportunity_id: UUID
    vendor_id: UUID
    match_score: float
    naics_overlap: float
    certification_match: bool
    capability_similarity: float
    past_performance_weight: float
    geographic_fit: float
    explanation: str
    factors: dict[str, Any]

    class Config:
        from_attributes = True


class OpportunityMatchUpdate(BaseModel):
    opportunity_id: UUID | None = None
    vendor_id: UUID | None = None
    match_score: float | None = None
    naics_overlap: float | None = None
    certification_match: bool | None = None
    capability_similarity: float | None = None
    past_performance_weight: float | None = None
    geographic_fit: float | None = None
    explanation: str | None = None
    factors: dict[str, Any] | None = None


class ProposalCreate(BaseModel):
    """A proposal draft linked to an opportunity"""

    opportunity_id: UUID
    vendor_id: UUID
    title: str
    status: str = Field(..., description="draft, review, submitted, awarded, lost")
    sections: dict[str, Any] = Field(..., description="Structured proposal sections")
    compliance_checklist: dict[str, Any]
    estimated_price: Decimal
    submission_deadline: datetime
    version_notes: str


class Proposal(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int = 1
    opportunity_id: UUID
    vendor_id: UUID
    title: str
    status: str
    sections: dict[str, Any]
    compliance_checklist: dict[str, Any]
    estimated_price: Decimal
    submission_deadline: datetime
    version_notes: str

    class Config:
        from_attributes = True


class ProposalUpdate(BaseModel):
    opportunity_id: UUID | None = None
    vendor_id: UUID | None = None
    title: str | None = None
    status: str | None = None
    sections: dict[str, Any] | None = None
    compliance_checklist: dict[str, Any] | None = None
    estimated_price: Decimal | None = None
    submission_deadline: datetime | None = None
    version_notes: str | None = None

