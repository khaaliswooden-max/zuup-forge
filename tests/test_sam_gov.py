"""Tests for SAM.gov integration (requires network and optional SAM_GOV_API_KEY)."""
from __future__ import annotations

import os

import pytest

from forge.integrations.sam_gov import SAMOpportunity, fetch_opportunities


@pytest.mark.asyncio
async def test_sam_gov_fetch() -> None:
    """Test SAM.gov API returns results (requires network and API key)."""
    if not os.environ.get("SAM_GOV_API_KEY"):
        pytest.skip("SAM_GOV_API_KEY not set; get a free key from SAM.gov Account Details")
    opps = await fetch_opportunities(keyword="cybersecurity", limit=5)
    assert len(opps) > 0
    assert opps[0].notice_id != ""
    assert opps[0].title != ""


def test_sam_opportunity_model() -> None:
    """Test SAMOpportunity model validation."""
    o = SAMOpportunity(
        notice_id="abc123",
        title="Test Opportunity",
        agency="GSA",
        source_url="https://sam.gov/opp/abc123/view",
    )
    assert o.notice_id == "abc123"
    assert o.title == "Test Opportunity"
    assert o.naics_codes == []
    assert o.set_asides == []
