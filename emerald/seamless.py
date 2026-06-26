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
        return self._request("POST", path, json=body)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{BASE_URL}{path}"
        resp = requests.request(method, url, headers=self._headers,
                                timeout=self.timeout, **kwargs)
        if resp.status_code in (401, 403):
            raise SeamlessError(
                f"{resp.status_code} from {url} — check SEAMLESS_API_KEY and that your "
                f"plan includes API access (Enterprise). Body: {resp.text[:300]}"
            )
        if not resp.ok:
            raise SeamlessError(f"{method} {url} -> {resp.status_code}: {resp.text[:400]}")
        return resp.json() if resp.content else {}

    # ---- raw endpoints ----
    def search_contacts(self, filters: dict[str, Any], limit: int = 25) -> Any:
        body = dict(filters)
        body["limit"] = limit
        return self._post("/search/contacts", body)

    def research_contacts(self, search_result_ids: list[str]) -> Any:
        return self._post("/contacts/research", {"searchResultIds": search_result_ids})

    def poll_research(self, request_ids: list[str]) -> Any:
        # GET with a comma-separated requestIds query param (per Seamless docs).
        return self._get("/contacts/research/poll",
                         params={"requestIds": ",".join(request_ids)})


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


# Seamless seniority enum (exact values).
_SENIORITY_ENUM = {"C-Level", "VP", "Director", "Manager", "Senior", "Entry Level",
                   "Mid-Level", "Other"}
# Default bands for a normal IC/mid role — deliberately omits C-Level & VP so the
# search stops surfacing CFOs/Chiefs for an individual-contributor opening.
_SENIORITY_DEFAULT = ["Mid-Level", "Senior", "Manager"]

# Map our job families to Seamless's department enum (only where it's a clean fit).
_DEPARTMENT_BY_FAMILY = {
    "finance": ["Finance"],
    "tech": ["Engineering", "IT"],
}


def map_seniority(text: str) -> list[str]:
    """Map a free-text seniority (from search_criteria) to Seamless enum bands."""
    t = (text or "").lower()
    bands: list[str] = []
    if any(k in t for k in ("chief", "c-level", "c-suite", "cxo", "ceo", "cfo",
                            "cto", "coo", "president")):
        bands.append("C-Level")
    if "vp" in t or "vice president" in t:
        bands.append("VP")
    if "director" in t or "head of" in t:
        bands.append("Director")
    if "manager" in t or "management" in t or "lead" in t or "supervisor" in t:
        bands.append("Manager")
    if "senior" in t or "individual contributor" in t or "ic" == t.strip():
        bands += ["Senior", "Mid-Level"]
    if "mid" in t:
        bands.append("Mid-Level")
    if any(k in t for k in ("junior", "entry", "associate", "new grad", "graduate")):
        bands += ["Entry Level", "Mid-Level"]
    if not bands:
        bands = list(_SENIORITY_DEFAULT)
    # de-dupe, preserve order, keep only valid enum values
    seen: set[str] = set()
    return [b for b in bands if b in _SENIORITY_ENUM and not (b in seen or seen.add(b))]


def criteria_to_filters(
    search_criteria: dict[str, Any], keywords: int = 0, job_type: str | None = None
) -> dict[str, Any]:
    """Translate Emerald's search_criteria into Seamless /search/contacts filters.

    Seamless ANDs every filter, and `contactKeyword` values are AND-combined — so
    sending many specific skill phrases tanks recall to zero. We lead with the high-
    signal, OR-style filters (job titles + state + seniority), and only add a couple
    of short keywords when explicitly asked (keywords>0). Recruiters narrow from there.

    Seniority is mapped from search_criteria.seniority (default mid/senior/manager,
    which excludes execs) — but SKIPPED for physicians, who don't fit corporate bands.
    """
    c = search_criteria or {}
    filters: dict[str, Any] = {"contactCountry": ["United States"]}

    titles = [t for t in (c.get("titles") or []) if t][:8]
    if titles:
        filters["jobTitle"] = titles

    states = _extract_states(c.get("location") or "")
    if states:
        filters["contactState"] = states

    if job_type != "physician":
        seniority = map_seniority(c.get("seniority") or "")
        if seniority:
            filters["seniority"] = seniority

    # Department sharpens precision for families that map cleanly to a Seamless dept.
    dept = _DEPARTMENT_BY_FAMILY.get(job_type or "")
    if dept:
        filters["department"] = dept

    if keywords > 0:
        # Prefer short, single-token skills (e.g. GAAP, ERP) — they AND less harshly.
        skills = sorted(
            (s for s in (c.get("skills") or []) if s and len(s.split()) <= 2),
            key=len,
        )[:keywords]
        if skills:
            filters["contactKeyword"] = skills

    return filters


_EXEC_RX = re.compile(
    r"\b(chief|ceo|cfo|cto|coo|cio|cxo|president|vice\s*president|vp|svp|evp|avp"
    r"|executive|director|partner|owner|founder|head\s+of|board\s+member)\b",
    re.I,
)


def _looks_exec(title: str | None) -> bool:
    """True if the title looks like an executive/owner (to drop for IC roles)."""
    return bool(title and _EXEC_RX.search(title))


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
    job_type: str | None = None,
) -> dict[str, Any]:
    """Search Seamless for candidates matching the criteria; optionally enrich.

    Returns {filters, total, candidates[], enriched(bool), error?}.
    """
    client = client or SeamlessClient()
    filters = criteria_to_filters(search_criteria, job_type=job_type)

    # Seamless ranks prominent (senior) profiles first and has no sort param, so for
    # non-exec roles we over-fetch and drop obvious executives client-side.
    wants_exec = any(
        b in (filters.get("seniority") or []) for b in ("C-Level", "VP", "Director")
    )
    fetch_limit = min(limit * 2, 100) if not wants_exec else limit
    res = client.search_contacts(filters, limit=fetch_limit)
    # The contacts array key varies; handle the common shapes defensively.
    rows = (
        res.get("contacts")
        or res.get("data")
        or res.get("results")
        or (res if isinstance(res, list) else [])
    )
    candidates = [_normalize(r) for r in rows if isinstance(r, dict)]
    if not wants_exec:
        candidates = [c for c in candidates if not _looks_exec(c.get("title"))]
    candidates = candidates[:limit]
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
    client: SeamlessClient, request_ids: list[str], attempts: int = 8, delay: float = 6.0
) -> list[dict[str, Any]]:
    """Poll the research endpoint until enrichment finishes (or attempts run out).

    Each record carries a `status`; we stop once every record is resolved
    (complete/duplicate/found) or already has a contact value, and keep polling
    while any are still 'pending'/'processing'. Transient errors (e.g. 502) retry.
    """
    done_states = {"complete", "completed", "duplicate", "found", "enriched", "failed"}
    results: list[dict[str, Any]] = []
    for _ in range(attempts):
        try:
            resp = client.poll_research(request_ids)
        except SeamlessError:
            time.sleep(delay)
            continue
        rows = [r for r in (resp.get("data") or resp.get("contacts")
                            or resp.get("results") or []) if isinstance(r, dict)]
        if rows:
            results = rows
            resolved = all(
                (r.get("status") or "complete").lower() in done_states
                or _first(r, "email", "personalEmail", "email1", "contactPhone1")
                for r in rows
            )
            if resolved:
                break
        time.sleep(delay)
    return results


def _first(record: dict[str, Any], *keys: str) -> str | None:
    """First non-empty value among the given keys."""
    for k in keys:
        v = record.get(k)
        if v:
            return v
    return None


def _merge_enrichment(candidates: list[dict[str, Any]], enriched: list[dict[str, Any]]) -> None:
    """Merge email/phone from enriched records onto candidates (Seamless field names).

    Emails: email / personalEmail / email1-3.  Phones: contactPhone1 / contactPhone2.
    Match by searchResultId; fall back to positional order when ids are absent.
    """
    by_id = {e.get("searchResultId"): e for e in enriched if e.get("searchResultId")}
    for i, c in enumerate(candidates):
        e = by_id.get(c["search_result_id"])
        if e is None and not by_id and i < len(enriched):
            e = enriched[i]  # positional fallback
        if not e:
            continue
        email = _first(e, "email", "personalEmail", "email1", "email2", "email3")
        phone = _first(e, "contactPhone1", "contactPhone2")
        if email:
            c["email"] = email
        if phone:
            c["phone"] = phone
