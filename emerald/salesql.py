"""SalesQL contact enrichment — FALLBACK provider.

Fills the email/phone that Seamless couldn't find, using a candidate's LinkedIn URL.
SalesQL's enrichment API is a paid feature (needs SALESQL_API_KEY). This client is
mock-first: with no key it is a harmless no-op, so the pipeline runs unchanged.

It only runs when EMERALD_ENRICH_PROVIDER is "salesql" or "both" AND SALESQL_API_KEY is
set (see settings.use_salesql_fallback), and only for candidates that are STILL missing
a contact after Seamless but do have a LinkedIn URL to look up.

NOTE: verify the endpoint + field names below against SalesQL's current API docs when
you enable this. They're centralized in the constants so a doc change is a one-line edit.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .config import settings

BASE_URL = "https://api.salesql.com/v1"
# The enrich-by-LinkedIn operation. Verify against SalesQL's API docs on enable.
ENRICH_PATH = "/persons/enrich"
# Response field names SalesQL returns for a resolved contact (checked in order).
_EMAIL_FIELDS = ("email", "emails", "work_email", "personal_email")
_PHONE_FIELDS = ("phone", "phones", "mobile", "phone_number")


class SalesQLError(RuntimeError):
    pass


class SalesQLClient:
    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or settings.salesql_api_key
        self.timeout = timeout
        if not self.api_key:
            raise SalesQLError(
                "SalesQL not configured. Set SALESQL_API_KEY (paid plan with API)."
            )

    def enrich_by_linkedin(self, linkedin_url: str) -> dict[str, str | None]:
        """Return {"email", "phone"} for a LinkedIn profile URL (either may be None)."""
        resp = requests.get(
            f"{BASE_URL}{ENRICH_PATH}",
            params={"api_key": self.api_key, "linkedin_url": linkedin_url},
            timeout=self.timeout,
        )
        if resp.status_code in (401, 403):
            raise SalesQLError(
                f"{resp.status_code} from SalesQL — check SALESQL_API_KEY / plan. "
                f"Body: {resp.text[:200]}"
            )
        if not resp.ok:
            raise SalesQLError(f"SalesQL {resp.status_code}: {resp.text[:200]}")
        data = resp.json() if resp.content else {}
        person = data.get("person") or data.get("data") or data
        return {
            "email": _first_contact(person, _EMAIL_FIELDS),
            "phone": _first_contact(person, _PHONE_FIELDS),
        }


def _first_contact(person: Any, fields: tuple[str, ...]) -> str | None:
    """First non-empty contact value; unwraps list-valued fields (e.g. emails[])."""
    if not isinstance(person, dict):
        return None
    for f in fields:
        v = person.get(f)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    item = item.get("value") or item.get("email") or item.get("phone")
                if item:
                    return str(item)
        elif v:
            return str(v)
    return None


def fill_missing_contacts(
    candidates: list[dict[str, Any]],
    limit: int = 20,
    client: SalesQLClient | None = None,
    pace: float = 0.4,
) -> dict[str, Any]:
    """Backfill email/phone (in place) for candidates Seamless left without contacts.

    Targets only candidates that are missing BOTH email and phone but have a LinkedIn
    URL (nothing to look up otherwise). Caps at `limit`. Never raises — returns
    {attempted, filled, error?}; per-candidate failures are skipped.
    """
    client = client or SalesQLClient()
    targets = [
        c for c in candidates
        if not (c.get("email") or c.get("phone")) and c.get("linkedin")
    ][:limit]
    attempted = filled = 0
    for i, cand in enumerate(targets):
        if i:
            time.sleep(pace)
        attempted += 1
        try:
            got = client.enrich_by_linkedin(cand["linkedin"])
        except SalesQLError:
            continue
        if got.get("email"):
            cand["email"] = got["email"]
        if got.get("phone"):
            cand["phone"] = got["phone"]
        if got.get("email") or got.get("phone"):
            cand["_contact_source"] = "salesql"
            filled += 1
    return {"attempted": attempted, "filled": filled}
