"""Minimal Loxo Open API client (Phase 1: write the JD + attach deliverables).

Verified facts this client encodes:
  - Base URL:   https://{domain}/api/{slug}
  - Auth:       Authorization: Bearer <API_KEY>
  - Create job: POST /api/{slug}/jobs   (NOT /api/v1/jobs -> that 403s)
  - Loxo requires job_type_id + a company assignment + salary on create.
  - Use GET /compensation_types and GET /job_types to discover valid IDs.

What the Open API CANNOT do (do these via Loxo-native Stage Automations, Phase 2):
  external candidate search, AI ranking, contact enrichment from the 1.2B graph.
"""
from __future__ import annotations

from typing import Any

import requests

from .config import settings


class LoxoError(RuntimeError):
    pass


class LoxoClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or settings.loxo_base_url or "").rstrip("/")
        self.api_key = api_key or settings.loxo_api_key
        self.timeout = timeout
        if not self.base_url or not self.api_key:
            raise LoxoError(
                "Loxo not configured. Set LOXO_DOMAIN, LOXO_SLUG, LOXO_API_KEY "
                "(see .env.example)."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.request(
            method, url, headers=self._headers, timeout=self.timeout, **kwargs
        )
        if resp.status_code == 403:
            raise LoxoError(
                f"403 from {url}. Check the API key AND that you're on the "
                f"/api/{{slug}} path (the /api/v1 path is not part of the Open API)."
            )
        if not resp.ok:
            raise LoxoError(f"{method} {url} -> {resp.status_code}: {resp.text[:500]}")
        return resp.json() if resp.content else {}

    # ---- discovery helpers (run these once to fill in your .env IDs) ----
    def job_types(self) -> Any:
        return self._request("GET", "/job_types")

    def compensation_types(self) -> Any:
        return self._request("GET", "/compensation_types")

    def companies(self, query: str | None = None) -> Any:
        params = {"query": query} if query else None
        return self._request("GET", "/companies", params=params)

    # ---- the Phase 1 write ----
    def create_job(
        self,
        title: str,
        description: str,
        job_type_id: str | int | None = None,
        company_id: str | int | None = None,
        salary: str | None = None,
        published: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /jobs. Created UNPUBLISHED by default (review before it goes live)."""
        job_type_id = job_type_id or settings.loxo_default_job_type_id
        company_id = company_id or settings.loxo_default_company_id
        if not job_type_id or not company_id:
            raise LoxoError(
                "Loxo requires job_type_id and company_id. Set "
                "LOXO_DEFAULT_JOB_TYPE_ID / LOXO_DEFAULT_COMPANY_ID, or pass them "
                "in. Discover IDs with client.job_types() and client.companies()."
            )
        # Loxo expects bracketed form params: job[title], job[description], ...
        data: dict[str, Any] = {
            "job[title]": title,
            "job[description]": description,
            "job[job_type_id]": job_type_id,
            "job[company_id]": company_id,
            "job[published]": str(published).lower(),
        }
        if salary:
            data["job[salary]"] = salary
        for k, v in (extra or {}).items():
            data[f"job[{k}]"] = v
        return self._request("POST", "/jobs", data=data)

    def activity_types(self) -> Any:
        """List activity types (to find a 'Note' type id for add_note)."""
        return self._request("GET", "/activity_types")

    def add_note(
        self,
        job_id: str | int,
        notes: str,
        activity_type_id: str | int | None = None,
        person_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Log a note/activity against a job via POST /person_events.

        Loxo's notes/activities are person_events. activity_type_id is required and
        is account-specific — set LOXO_NOTE_ACTIVITY_TYPE_ID (discover via
        activity_types()).
        """
        activity_type_id = activity_type_id or settings.loxo_note_activity_type_id
        if not activity_type_id:
            raise LoxoError(
                "add_note needs an activity_type_id. Set LOXO_NOTE_ACTIVITY_TYPE_ID "
                "(discover via client.activity_types())."
            )
        data: dict[str, Any] = {
            "person_event[job_id]": job_id,
            "person_event[activity_type_id]": activity_type_id,
            "person_event[notes]": notes,
        }
        if person_id:
            data["person_event[person_id]"] = person_id
        return self._request("POST", "/person_events", data=data)

    def create_person(
        self,
        name: str,
        current_title: str | None = None,
        current_company: str | None = None,
        location: str | None = None,
        linkedin_url: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a person (candidate) via POST /people.

        Loxo expects bracketed form params; emails/phones are nested arrays, so we
        send a list of (key, value) tuples to allow repeats. Loxo auto-merges
        duplicates by contact info / LinkedIn (Settings -> Data enrichment), so
        re-pushing the same candidate folds into the existing record.

        NOTE: current_title / current_company are NOT settable here — Loxo derives
        them from work history. They're accepted as args (callers pass them) but
        surfaced elsewhere (e.g. the pipeline note), not on the person create.
        """
        data: list[tuple[str, Any]] = [("person[name]", name or "Unknown")]
        for key, val in (
            ("person[location]", location),
            ("person[linkedin_url]", linkedin_url),
        ):
            if val:
                data.append((key, val))
        for e in emails or []:
            if e:
                data.append(("person[emails][][value]", e))
        for p in phones or []:
            if p:
                data.append(("person[phones][][value]", p))
        return self._request("POST", "/people", data=data)

    # ---- pipeline reads/writes (mainly used in B2; handy for B1 verification) ----
    def get_job_pipeline(self, job_id: str | int) -> Any:
        """GET /jobs/{id}/candidates — everyone on the job + their stage."""
        return self._request("GET", f"/jobs/{job_id}/candidates")

    def add_to_pipeline(
        self,
        job_id: str | int,
        person_id: str | int,
        notes: str | None = None,
        activity_type_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Add an existing person to a job's pipeline (lands at the Sourced stage).

        Implemented as a workflow-stage person_event ('Sourced' by default), matching
        Loxo's own model. The activity type is account-specific — set
        LOXO_SOURCED_ACTIVITY_TYPE_ID (discover via activity_types()).
        """
        activity_type_id = activity_type_id or settings.loxo_sourced_activity_type_id
        data: dict[str, Any] = {
            "person_event[person_id]": person_id,
            "person_event[job_id]": job_id,
            "person_event[activity_type_id]": activity_type_id,
        }
        if notes:
            data["person_event[notes]"] = notes
        return self._request("POST", "/person_events", data=data)
