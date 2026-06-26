"""Seamless.AI client — source candidates from a job's search_criteria.

Flow (per Seamless docs, June 2026):
  POST /search/contacts    -> candidates (searchResultId + profile)   [sync]
  POST /contacts/research  -> {requestIds}                            [async, spends credits]
  POST /contacts/research/poll -> enriched email/phone               [poll]

Auth: header  Token: <SEAMLESS_API_KEY>.  Base: https://api.seamless.ai/api/client/v1

Sourcing turns the generated `search_criteria` into Seamless filters, runs the
search, and (optionally) enriches the top results with contact info. Enrichment
spends Seamless credits, so it's OFF by default and capped.
"""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from .config import settings

BASE_URL = "https://api.seamless.ai/api/client/v1"

# Minimal US state map so a free-text location ("Cleveland, OH"; "New York,
# New Jersey, CT") can be turned into Seamless `contactState` values (full names).
_STATES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
    "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware",
    "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho",
    "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas",
    "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland",
    "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
    "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada",
    "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
    "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma",
    "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina",
    "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas", "ut": "Utah",
    "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia",
    "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia",
}
_STATE_NAMES = {v.lower(): v for v in _STATES.values()}


class SeamlessError(RuntimeError):
    pass


class SeamlessClient:
    def __init__(self, api_key: str | None = None, timeout: int = 45):
        self.api_key = api_key or settings.seamless_api_key
        self.timeout = timeout
        if not self.api_key:
            raise SeamlessError(
                "Seamless not configured. Set SEAMLESS_API_KEY in .env (the API is a "
                "paid Enterprise feature)."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Token": self.api_key, "Content-Type": "application/json"}

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, headers=self._headers, json=body, timeout=self.timeout)
        if resp.status_code in (401, 403):
            raise SeamlessError(
                f"{resp.status_code} from {url} — check SEAMLESS_API_KEY and that your "
                f"plan includes API access (Enterprise). Body: {resp.text[:300]}"
            )
        if not resp.ok:
            raise SeamlessError(f"POST {url} -> {resp.status_code}: {resp.text[:400]}")
        return resp.json() if resp.content else {}

    # ---- raw endpoints ----
    def search_contacts(self, filters: dict[str, Any], limit: int = 25) -> Any:
        body = dict(filters)
        body["limit"] = limit
        return self._post("/search/contacts", body)

    def research_contacts(self, search_result_ids: list[str]) -> Any:
        return self._post("/contacts/research", {"searchResultIds": search_result_ids})

    def poll_research(self, request_ids: list[str]) -> Any:
        return self._post("/contacts/research/poll", {"requestIds": request_ids})


# ---- mapping: generated search_criteria -> Seamless filters ----
def _extract_states(location: str) -> list[str]:
    """Find US states anywhere in a free-text location string.

    Matches full names (case-insensitive substring) and 2-letter abbreviations
    (as standalone uppercase tokens, e.g. "OH"), so "Independence, OH / Cleveland
    metro" -> ["Ohio"], and "New York, NJ, CT" -> ["New York", "New Jersey", ...].
    """
    found: list[str] = []
    low = location.lower()
    for name_l, name in _STATE_NAMES.items():
        if name_l in low and name not in found:
            found.append(name)
    for abbr, name in _STATES.items():
        if re.search(rf"\b{abbr.upper()}\b", location) and name not in found:
            found.append(name)
    return found


def criteria_to_filters(
    search_criteria: dict[str, Any], keywords: int = 0
) -> dict[str, Any]:
    """Translate Emerald's search_criteria into Seamless /search/contacts filters.

    Seamless ANDs every filter, and `contactKeyword` values are AND-combined — so
    sending many specific skill phrases tanks recall to zero. We lead with the high-
    signal, OR-style filters (job titles + state), and only add a couple of short
    keywords when explicitly asked (keywords>0). Recruiters narrow from there.
    """
    c = search_criteria or {}
    filters: dict[str, Any] = {"contactCountry": ["United States"]}

    titles = [t for t in (c.get("titles") or []) if t][:8]
    if titles:
        filters["jobTitle"] = titles

    states = _extract_states(c.get("location") or "")
    if states:
        filters["contactState"] = states

    if keywords > 0:
        # Prefer short, single-token skills (e.g. GAAP, ERP) — they AND less harshly.
        skills = sorted(
            (s for s in (c.get("skills") or []) if s and len(s.split()) <= 2),
            key=len,
        )[:keywords]
        if skills:
            filters["contactKeyword"] = skills

    return filters


def _normalize(contact: dict[str, Any]) -> dict[str, Any]:
    """Pull the fields we care about out of a Seamless search-result contact."""
    name = contact.get("name") or " ".join(
        x for x in (contact.get("firstName"), contact.get("lastName")) if x
    )
    loc = ", ".join(
        x for x in (contact.get("city"), contact.get("state"), contact.get("country")) if x
    )
    return {
        "search_result_id": contact.get("searchResultId"),
        "name": name,
        "title": contact.get("title"),
        "company": contact.get("company"),
        "location": loc,
        "linkedin": contact.get("liUrl"),
        "email": contact.get("email"),   # populated after enrichment
        "phone": contact.get("phone"),   # populated after enrichment
    }


def source_candidates(
    search_criteria: dict[str, Any],
    limit: int = 50,
    enrich: bool = False,
    enrich_top_n: int = 10,
    client: SeamlessClient | None = None,
) -> dict[str, Any]:
    """Search Seamless for candidates matching the criteria; optionally enrich.

    Returns {filters, total, candidates[], enriched(bool), error?}.
    """
    client = client or SeamlessClient()
    filters = criteria_to_filters(search_criteria)

    res = client.search_contacts(filters, limit=limit)
    # The contacts array key varies; handle the common shapes defensively.
    rows = (
        res.get("contacts")
        or res.get("data")
        or res.get("results")
        or (res if isinstance(res, list) else [])
    )
    candidates = [_normalize(r) for r in rows if isinstance(r, dict)]
    total = (res.get("supplementalData") or {}).get("total") if isinstance(res, dict) else None

    out: dict[str, Any] = {
        "filters": filters,
        "total": total,
        "candidates": candidates,
        "enriched": False,
    }

    if enrich and candidates:
        ids = [c["search_result_id"] for c in candidates[:enrich_top_n] if c["search_result_id"]]
        if ids:
            try:
                started = client.research_contacts(ids)
                request_ids = started.get("requestIds") or []
                enriched = _poll_until_ready(client, request_ids)
                _merge_enrichment(candidates, enriched)
                out["enriched"] = True
            except SeamlessError as e:
                out["enrich_error"] = str(e)

    return out


def _poll_until_ready(
    client: SeamlessClient, request_ids: list[str], attempts: int = 6, delay: float = 5.0
) -> list[dict[str, Any]]:
    """Poll the research endpoint until results land (or attempts run out)."""
    results: list[dict[str, Any]] = []
    for _ in range(attempts):
        resp = client.poll_research(request_ids)
        rows = resp.get("contacts") or resp.get("results") or resp.get("data") or []
        if rows:
            results = [r for r in rows if isinstance(r, dict)]
            if not resp.get("isMore") and not resp.get("pending"):
                break
        time.sleep(delay)
    return results


def _merge_enrichment(candidates: list[dict[str, Any]], enriched: list[dict[str, Any]]) -> None:
    """Merge email/phone from enriched records back onto the candidate list by id."""
    by_id = {e.get("searchResultId"): e for e in enriched if e.get("searchResultId")}
    for c in candidates:
        e = by_id.get(c["search_result_id"])
        if not e:
            continue
        emails = e.get("emails") or ([e["email"]] if e.get("email") else [])
        phones = e.get("phones") or e.get("phoneNumbers") or ([e["phone"]] if e.get("phone") else [])
        if emails:
            c["email"] = emails[0] if isinstance(emails, list) else emails
        if phones:
            c["phone"] = phones[0] if isinstance(phones, list) else phones
