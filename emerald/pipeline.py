"""Orchestrator: transcript -> deliverables -> (optional) Loxo write.

    run_pipeline(transcript, client_name, push_to_loxo=False) -> result dict
"""
from __future__ import annotations

import html as _html
import json
import os
from datetime import datetime, timezone
from typing import Any

from .config import settings
from .generate import generate_deliverables
from .handoff import build_sourcing_brief
from .redact import redact

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
# Durable, per-job store for the fetched candidate long list (+ their contacts).
CANDIDATES_DIR = os.path.join(OUTPUT_DIR, "candidates")

# The ordered JD body sections, as (heading, jd-key) pairs. Shared by both renderers
# so the markdown preview and the HTML pushed to Loxo stay in lockstep.
_JD_SECTIONS = (
    ("Responsibilities", "responsibilities"),
    ("Requirements", "requirements"),
    ("Why Join", "why_join"),
)


def _comp_line(d: dict[str, Any]) -> str | None:
    comp = d.get("comp") or {}
    if not (comp.get("min") or comp.get("max")):
        return None
    cur = comp.get("currency", "USD")
    per = comp.get("period", "year")
    return f"{cur} {comp.get('min','?')}–{comp.get('max','?')} / {per}"


def render_description(d: dict[str, Any]) -> str:
    """Build a plain-text/markdown JD body for the saved artifact + web preview.

    Deliberately hashtag-free: headings are plain lines (no `#`), so nothing renders
    as a stray "#" anywhere the JD is shown. The Loxo Description tab gets the HTML
    version (render_description_html) instead.
    """
    jd = d.get("jd", {})
    lines = [d.get("title", "Open Role"), "", jd.get("summary", ""), ""]
    for heading, key in _JD_SECTIONS:
        if jd.get(key):
            lines += [heading, *[f"- {item}" for item in jd[key]], ""]
    comp = _comp_line(d)
    if comp:
        lines += [f"Compensation: {comp}"]
    return "\n".join(lines).strip()


def render_description_html(d: dict[str, Any]) -> str:
    """Build the JD body as clean HTML for Loxo's Description tab (rich-text field).

    Loxo renders the description as HTML, so we emit real <h2>/<h3>/<ul> — headings
    show as headings, not literal "#" hashtags. This is what gets pushed on job create.
    """
    def esc(x: Any) -> str:
        return _html.escape(str(x if x is not None else ""))

    jd = d.get("jd", {})
    parts = [f"<h2>{esc(d.get('title', 'Open Role'))}</h2>"]
    if jd.get("summary"):
        parts.append(f"<p>{esc(jd['summary'])}</p>")
    for heading, key in _JD_SECTIONS:
        items = jd.get(key)
        if items:
            parts.append(f"<h3>{heading}</h3>")
            parts.append("<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>")
    comp = _comp_line(d)
    if comp:
        parts.append(f"<p><strong>Compensation:</strong> {esc(comp)}</p>")
    return "\n".join(parts)


def store_candidates(
    key: str | int,
    title: str | None,
    candidates: list[dict[str, Any]],
    enriched: bool = False,
) -> str:
    """Persist the fetched candidate list (+ contacts) to a durable, per-job file.

    Keyed by the Loxo job id when there is one (else a title slug), so the sourced
    long list and any gathered email/phone live in one predictable place:
    output/candidates/<key>.json. Re-running the same job overwrites it.
    """
    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    safe = "".join(c for c in str(key) if c.isalnum() or c in "-_") or "job"
    path = os.path.join(CANDIDATES_DIR, f"{safe}.json")
    payload = {
        "job_key": str(key),
        "title": title,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "count": len(candidates),
        "enriched": enriched,
        "with_contacts": sum(1 for c in candidates if c.get("email") or c.get("phone")),
        "candidates": candidates,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def _salary_str(comp: dict[str, Any] | None) -> str | None:
    comp = comp or {}
    if comp.get("min") and comp.get("max"):
        return f"{comp['min']}-{comp['max']}"
    return None


def _resolve_person_id(client: Any, cand: dict[str, Any]) -> tuple[Any, bool]:
    """Return (person_id, created) for a candidate, deduping by email.

    If the candidate has an email that already maps to a Loxo person, reuse that
    person (upsert — no duplicate). Otherwise create the person, sending along any
    email/phone/linkedin so contacts land on the record. Loxo also auto-merges by
    contact/LinkedIn, so a create still folds into an existing record.
    """
    existing = client.find_person_by_email(cand.get("email"))
    if isinstance(existing, dict) and existing.get("id"):
        return existing["id"], False
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
    return pid, True


def _pipeline_note(cand: dict[str, Any], source: str = "Seamless") -> str | None:
    """The recruiter-facing note logged when a candidate lands on the job pipeline."""
    ctx = " ".join(
        x for x in (cand.get("title"),
                    f"@ {cand['company']}" if cand.get("company") else "") if x
    )
    return f"Sourced via {source} — {ctx}".strip(" —") or None


def push_sourced_candidates(
    job_id: str | int,
    candidates: list[dict[str, Any]],
    client: Any = None,
    pace: float = 0.6,
) -> dict[str, Any]:
    """Upsert each sourced candidate as a Loxo person and add it to the job pipeline.

    Deduped by email (see _resolve_person_id) so re-pushing doesn't create duplicates,
    and any gathered email/phone rides onto the person record. Slow by design: Loxo
    rate-limits bursts, so we pace ~`pace`s between people — a 150-candidate push takes
    several minutes. Callers that must return quickly (the web UI) run this in the
    background; the CLI calls it inline. Never raises: per-candidate failures are
    collected and returned as {created, errors}.
    """
    import time

    if client is None:
        from .loxo import LoxoClient  # lazy: only needed when actually pushing

        client = LoxoClient()

    pushed, errors = 0, []
    for i, cand in enumerate(candidates):
        if i:
            time.sleep(pace)  # gentle pacing — Loxo rate-limits bursts
        try:
            pid, _created = _resolve_person_id(client, cand)
            if pid:
                client.add_to_pipeline(job_id, pid, notes=_pipeline_note(cand))
                pushed += 1
        except Exception as e:
            errors.append(f"{cand.get('name')}: {e}")
    return {"created": pushed, "errors": errors}


def push_contacts_to_loxo(
    candidates: list[dict[str, Any]],
    job_id: str | int | None = None,
    client: Any = None,
    pace: float = 0.6,
) -> dict[str, Any]:
    """Sync candidates that HAVE contacts (email/phone) into Loxo person records.

    This is the "put the fetched contacts into Loxo" step (upsert by email so an
    existing person is updated in place rather than duplicated). Only candidates with
    an email or phone are synced — the point is to land contact info. When a job_id is
    given, each synced person is also added to that job's pipeline. Never raises;
    returns {total, created, matched, attached, errors}.
    """
    import time

    if client is None:
        from .loxo import LoxoClient

        client = LoxoClient()

    with_contact = [c for c in candidates if c.get("email") or c.get("phone")]
    created = matched = attached = 0
    errors: list[str] = []
    for i, cand in enumerate(with_contact):
        if i:
            time.sleep(pace)
        try:
            pid, was_created = _resolve_person_id(client, cand)
            if not pid:
                errors.append(f"{cand.get('name')}: no person id returned")
                continue
            created += int(was_created)
            matched += int(not was_created)
            if job_id:
                client.add_to_pipeline(job_id, pid, notes=_pipeline_note(cand))
                attached += 1
        except Exception as e:
            errors.append(f"{cand.get('name')}: {e}")
    return {
        "total": len(with_contact),
        "created": created,
        "matched": matched,
        "attached": attached,
        "errors": errors,
    }


def load_candidate_store(name: str) -> dict[str, Any]:
    """Load a per-job candidate store file (output/candidates/<name>.json)."""
    safe = os.path.basename(name)
    path = os.path.join(CANDIDATES_DIR, safe)
    with open(path) as f:
        return json.load(f)


def run_pipeline(
    transcript: str,
    client_name: str = "",
    push_to_loxo: bool = False,
    publish: bool = False,
    save_artifact: bool = True,
    job_type: str | None = None,
    source: bool = False,
    source_limit: int | None = None,
    enrich_contacts: bool = False,
    push_candidates: bool = False,
    filter_boolean: str | None = None,
) -> dict[str, Any]:
    """Run the full Phase 1 flow. Returns a result dict with all deliverables.

    job_type selects a family profile (physician/finance/tech/lab/general); None
    auto-detects from the transcript. publish=True creates the job live on the
    careers page instead of unpublished (JD is already anonymized, but default stays
    unpublished for human review).
    """
    # Default the long-list size to the configured target (spec: 75–150).
    if source_limit is None:
        source_limit = settings.source_limit

    # 1) Generate (Claude, or offline mock if no key)
    deliverables = generate_deliverables(transcript, client_name, job_type=job_type)

    # 2) Anonymization safety-net
    deliverables, masked = redact(deliverables, client_name=client_name)

    description_md = render_description(deliverables)     # hashtag-free preview/artifact
    description_html = render_description_html(deliverables)  # for Loxo's Description tab

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "client_name_input": client_name,
        "redaction_hits": masked,
        "used_mock_generation": deliverables.get("_mock", False),
        "job_type": deliverables.get("_job_type", "general"),
        "deliverables": deliverables,
        "job_description_markdown": description_md,
        "job_description_html": description_html,
        "loxo": None,
    }

    # 3) Optional Loxo write (job created UNPUBLISHED for human review)
    job_id = None
    if push_to_loxo:
        from .loxo import LoxoClient  # imported lazily so dry-runs need no creds

        client = LoxoClient()
        job = client.create_job(
            title=deliverables.get("title", "Confidential Search"),
            description=description_html,  # HTML -> renders cleanly in the Description tab
            salary=_salary_str(deliverables.get("comp")),
            published=publish,
        )
        result["loxo"] = {"job": job}
        # Loxo wraps the created job as {"job": {"id": ...}}; unwrap if needed.
        job_obj = job.get("job", job) if isinstance(job, dict) else {}
        job_id = job_obj.get("id") if isinstance(job_obj, dict) else None
        result["loxo"]["job_id"] = job_id  # let callers schedule a background push
        # Clickable Loxo UI link for the created job (the recruiter app, not the
        # API path). Jobs auto-belong to LOXO_DEFAULT_OWNER_EMAILS when set (so they
        # show under that recruiter's My Jobs); this direct link opens them either way.
        agency_id = job_obj.get("agency_id") if isinstance(job_obj, dict) else None
        if job_id and agency_id and settings.loxo_domain:
            result["loxo"]["job_url"] = (
                f"https://{settings.loxo_domain}/agencies/{agency_id}/jobs/{job_id}"
            )

    # 4) Build the B1 recruiter handoff (Sourcing Brief). Always produced.
    brief_md = build_sourcing_brief(deliverables, job_id=job_id)
    result["sourcing_brief_markdown"] = brief_md

    # On push, post the brief as a note on the job so recruiters have it in Loxo.
    if push_to_loxo and job_id and settings.loxo_note_activity_type_id:
        try:
            client.add_note(job_id, brief_md)  # type: ignore[union-attr]
            result["loxo"]["note_added"] = True
        except Exception as e:  # note schema varies by account; don't fail the run
            result["loxo"]["note_error"] = str(e)
    elif push_to_loxo and job_id:
        result["loxo"]["note_skipped"] = "set LOXO_NOTE_ACTIVITY_TYPE_ID to post the brief"

    # 4b) Optional candidate sourcing via Seamless.AI (once the JD/Booleans exist).
    #     Maps the generated search_criteria -> Seamless filters -> candidates.
    #     Never fails the run: errors are captured on the result.
    if source:
        if not settings.has_seamless:
            result["sourcing"] = {"error": "SEAMLESS_API_KEY not set (Enterprise API)."}
        else:
            from .seamless import source_candidates  # lazy import

            try:
                result["sourcing"] = source_candidates(
                    deliverables.get("search_criteria", {}),
                    limit=source_limit,
                    enrich=enrich_contacts,
                    enrich_top_n=settings.enrich_top_n,  # keep in sync with the brief (top 15–20)
                    job_type=deliverables.get("_job_type"),
                )
            except Exception as e:  # don't let sourcing crash the pipeline
                result["sourcing"] = {"error": str(e)}

        # 4b-ii) SalesQL fallback: backfill contacts Seamless couldn't find (by LinkedIn
        #        URL). Only when enrichment was requested and SalesQL is enabled + keyed.
        if (
            enrich_contacts
            and settings.use_salesql_fallback
            and (result.get("sourcing") or {}).get("candidates")
        ):
            from .salesql import fill_missing_contacts  # lazy import

            try:
                result["sourcing"]["salesql"] = fill_missing_contacts(
                    result["sourcing"]["candidates"], limit=settings.enrich_top_n
                )
            except Exception as e:  # fallback must never crash the pipeline
                result["sourcing"]["salesql"] = {"error": str(e)}

        # 4c) Boolean pre-screen: keep only candidates matching the filter and drop
        #     ("shoot") the rest BEFORE anything reaches Loxo. `auto` uses the
        #     generated generic Boolean; otherwise pass an explicit expression.
        if filter_boolean and (result.get("sourcing") or {}).get("candidates"):
            from .boolean_filter import filter_candidates

            expr = filter_boolean
            if expr.strip().lower() == "auto":
                expr = (deliverables.get("boolean_strings") or {}).get("generic", "")
            kept, dropped = filter_candidates(result["sourcing"]["candidates"], expr)
            result["sourcing"]["candidates"] = kept
            result["sourcing"]["filter"] = {
                "expression": expr, "kept": len(kept), "dropped": len(dropped),
            }

        # Optionally push sourced candidates into the Loxo job pipeline (B2 headless):
        # create each as a Loxo person, then add to the job. Needs a created job_id.
        cands = (result.get("sourcing") or {}).get("candidates") or []
        if push_candidates and cands:
            if not job_id:
                result["sourcing"]["push_error"] = "need --push (a Loxo job) to attach candidates"
            else:
                result["sourcing"]["pushed_to_loxo"] = push_sourced_candidates(
                    job_id, cands, client=client
                )

    # 5) Persist artifacts (JSON + the human-readable brief). Gitignored.
    if save_artifact:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = "".join(c for c in deliverables.get("title", "job").lower()
                       if c.isalnum() or c in " -").strip().replace(" ", "-")[:40]
        base = os.path.join(OUTPUT_DIR, f"{stamp}_{slug}")
        with open(f"{base}.json", "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        with open(f"{base}_sourcing-brief.md", "w") as f:
            f.write(brief_md)
        result["artifact_path"] = f"{base}.json"
        result["brief_path"] = f"{base}_sourcing-brief.md"
        # Candidate list as a CSV the recruiter can work from.
        cands = (result.get("sourcing") or {}).get("candidates")
        if cands:
            import csv
            cand_path = f"{base}_candidates.csv"
            with open(cand_path, "w", newline="") as f:
                w = csv.DictWriter(
                    f, fieldnames=["name", "title", "company", "location",
                                   "linkedin", "email", "phone"]
                )
                w.writeheader()
                for c in cands:
                    w.writerow({k: c.get(k, "") for k in w.fieldnames})
            result["candidates_path"] = cand_path
            # Durable, per-job store keyed by Loxo job id (or title slug when no push):
            # the fetched candidates + any gathered contacts, in one predictable place.
            result["candidate_store_path"] = store_candidates(
                job_id or slug,
                deliverables.get("title"),
                cands,
                enriched=(result.get("sourcing") or {}).get("enriched", False),
            )

    return result
