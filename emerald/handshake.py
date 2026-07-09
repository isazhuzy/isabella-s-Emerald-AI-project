"""Handshake applicants -> Boolean screen -> Loxo pipeline.

Handshake has NO public employer API for applicants, and its prebuilt ATS syncs
(Workday, iCIMS, Greenhouse, SuccessFactors...) are Enterprise-only and don't
include Loxo. What every employer tier DOES have is the per-job
"Download Applicant Data (CSV)" export (and new-applicant notification emails).

This module ingests that CSV: normalize rows into candidate dicts that
boolean_filter.candidate_text() can screen, then create the survivors as Loxo
people and drop them onto the job's pipeline (same create_person +
add_to_pipeline pattern the sourcing pipeline uses).

Handshake's CSV headers vary by report/tier, so mapping is fuzzy: known headers
land in the fields the screener searches (name/email/school/major/...), and
every unrecognized non-empty column is folded into `headline` — a Boolean can
therefore match ANY column in the export (GPA, grad date, work auth, skills).
"""
from __future__ import annotations

import csv
import io
import re
import time
from typing import Any

# normalized CSV header -> candidate dict key ("_first"/"_last" merge into name)
_HEADER_MAP = {
    "name": "name", "full name": "name", "applicant name": "name",
    "student name": "name", "applicant": "name", "candidate name": "name",
    "first name": "_first", "preferred name": "_first", "last name": "_last",
    "email": "email", "email address": "email", "school email": "email",
    "phone": "phone", "phone number": "phone", "mobile": "phone",
    "school": "school", "institution": "school", "college": "school",
    "school name": "school", "education": "school",
    "major": "major", "majors": "major", "field of study": "major",
    "degree": "degree", "degree type": "degree", "education level": "degree",
    "title": "title", "current title": "title", "job title": "title",
    "company": "company", "current company": "company", "employer": "company",
    "location": "location", "city": "location", "hometown": "location",
    "work location": "location",
    "linkedin": "linkedin", "linkedin url": "linkedin",
}


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", (h or "").replace("_", " ").replace("-", " ")).strip().lower()


def parse_applicants_csv(text: str) -> list[dict[str, Any]]:
    """Parse a Handshake applicant-data CSV export into candidate dicts."""
    text = (text or "").lstrip("﻿").strip()
    if not text:
        return []
    out: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(text)):
        cand: dict[str, Any] = {}
        extras: list[str] = []
        first = last = ""
        for header, value in row.items():
            value = (value or "").strip()
            if not value:
                continue
            key = _HEADER_MAP.get(_norm_header(header or ""))
            if key == "_first":
                first = value
            elif key == "_last":
                last = value
            elif key and key not in cand:
                cand[key] = value
            else:  # unknown column -> searchable, and shown on the row label
                extras.append(f"{header.strip()}: {value}" if header else value)
        if not cand.get("name") and (first or last):
            cand["name"] = f"{first} {last}".strip()
        if extras:
            cand["headline"] = " · ".join(extras)
        if cand:
            cand["source"] = "handshake"
            out.append(cand)
    return out


def push_applicants(
    applicants: list[dict[str, Any]],
    job_id: str | int,
    source_label: str = "Handshake applicant",
) -> dict[str, Any]:
    """Create each applicant as a Loxo person and add them to the job pipeline.

    Same shape as the sourcing push in pipeline.run_pipeline: person create ->
    unwrap {"person": {...}} -> add_to_pipeline with a context note. Never raises
    per-candidate; errors are collected and reported.
    """
    from .loxo import LoxoClient  # lazy — page must render without Loxo keys

    client = LoxoClient()
    pushed, errors = 0, []
    for i, cand in enumerate(applicants):
        if i:
            time.sleep(0.6)  # gentle pacing — Loxo rate-limits bursts
        try:
            person = client.create_person(
                name=cand.get("name") or "Unknown",
                current_title=cand.get("title"),
                current_company=cand.get("company"),
                location=cand.get("location"),
                linkedin_url=cand.get("linkedin"),
                emails=[cand["email"]] if cand.get("email") else None,
                phones=[cand["phone"]] if cand.get("phone") else None,
            )
            pobj = person.get("person", person) if isinstance(person, dict) else {}
            pid = pobj.get("id") if isinstance(pobj, dict) else None
            if not pid:
                errors.append(f"{cand.get('name')}: Loxo returned no person id")
                continue
            ctx = " · ".join(
                x for x in (cand.get("school"), cand.get("major"), cand.get("degree"))
                if x
            )
            client.add_to_pipeline(
                job_id, pid, notes=f"{source_label} — {ctx}".strip(" —") or None
            )
            pushed += 1
        except Exception as e:
            errors.append(f"{cand.get('name')}: {e}")
    return {"created": pushed, "errors": errors}
