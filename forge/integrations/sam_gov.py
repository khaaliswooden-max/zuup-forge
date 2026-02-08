"""SAM.gov Opportunities API client.

API docs: https://open.gsa.gov/api/get-opportunities-public-api/
Public API requires an API key (free from SAM.gov Account Details).
Set SAM_GOV_API_KEY in the environment for requests.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from pydantic import BaseModel

SAM_BASE = "https://api.sam.gov/opportunities/v2/search"


class SAMOpportunity(BaseModel):
    """One opportunity from SAM.gov search."""

    notice_id: str
    title: str
    agency: Optional[str] = None
    sub_agency: Optional[str] = None
    naics_codes: list[str] = []
    set_asides: list[str] = []
    response_deadline: Optional[datetime] = None
    estimated_value: Optional[float] = None
    place_of_performance: Optional[str] = None
    solicitation_type: Optional[str] = None
    full_text: str = ""
    source_url: str = ""


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _format_place_of_performance(pop: Any) -> Optional[str]:
    """Format placeOfPerformance JSON to a short string."""
    if not pop or not isinstance(pop, dict):
        return None
    parts = []
    city = pop.get("city")
    if isinstance(city, dict) and city.get("name"):
        parts.append(city["name"])
    elif isinstance(city, str):
        parts.append(city)
    state = pop.get("state")
    if isinstance(state, dict) and state.get("code"):
        parts.append(state["code"])
    elif isinstance(state, str):
        parts.append(state)
    if pop.get("zip"):
        parts.append(str(pop["zip"]))
    return ", ".join(parts) if parts else None


async def fetch_opportunities(
    keyword: str = "",
    posted_from: Optional[str] = None,
    posted_to: Optional[str] = None,
    limit: int = 100,
    api_key: Optional[str] = None,
) -> list[SAMOpportunity]:
    """Fetch opportunities from SAM.gov public API.

    API key is required by SAM.gov. Pass api_key or set env SAM_GOV_API_KEY.
    """
    if not posted_from:
        posted_from = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
    if not posted_to:
        posted_to = datetime.now().strftime("%m/%d/%Y")
    if api_key is None:
        api_key = os.environ.get("SAM_GOV_API_KEY")

    params: dict[str, Any] = {
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": min(limit, 1000),
        "offset": 0,
    }
    if keyword:
        params["title"] = keyword  # SAM.gov v2 uses "title" for keyword search
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(SAM_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results: list[SAMOpportunity] = []
    raw_list = data.get("opportunitiesData") or data.get("opportunities") or []
    for opp in raw_list:
        notice_id = opp.get("noticeId", "")
        full_path = opp.get("fullParentPathName") or ""
        path_parts = [p.strip() for p in full_path.split(".") if p.strip()]
        agency = path_parts[0] if path_parts else None
        sub_agency = path_parts[-1] if len(path_parts) > 1 else None

        set_asides: list[str] = []
        if opp.get("typeOfSetAside"):
            set_asides.append(str(opp["typeOfSetAside"]))
        if opp.get("typeOfSetAsideDescription") and opp["typeOfSetAsideDescription"] not in set_asides:
            set_asides.append(str(opp["typeOfSetAsideDescription"]))

        naics = opp.get("naicsCode")
        naics_codes = [naics] if isinstance(naics, str) and naics else []
        if isinstance(naics, list):
            naics_codes = [str(c) for c in naics]

        award = opp.get("award") or {}
        amount = award.get("amount")
        if amount is not None:
            try:
                estimated_value = float(amount)
            except (TypeError, ValueError):
                estimated_value = None
        else:
            estimated_value = None

        desc = opp.get("description") or ""
        full_text = desc if isinstance(desc, str) and not desc.startswith("http") else ""

        ui_link = opp.get("uiLink") or ""
        source_url = ui_link or f"https://sam.gov/opp/{notice_id}/view" if notice_id else ""

        results.append(
            SAMOpportunity(
                notice_id=notice_id,
                title=opp.get("title", ""),
                agency=agency,
                sub_agency=sub_agency,
                naics_codes=naics_codes,
                set_asides=set_asides,
                response_deadline=_parse_date(opp.get("responseDeadLine") or opp.get("reponseDeadLine")),
                estimated_value=estimated_value,
                place_of_performance=_format_place_of_performance(opp.get("placeOfPerformance")),
                solicitation_type=opp.get("type"),
                full_text=full_text[:10000] if full_text else "",
                source_url=source_url,
            )
        )
    return results
