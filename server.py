"""Self-hosted web UI + webhook receiver for Emerald.

Run:  uvicorn server:app --reload --port 8000
  - Web UI:   http://localhost:8000/      (paste a transcript in the browser, click Run)
  - Webhook:  POST /webhook/transcript    (transcription vendor -> pipeline, hands-off)

This is entirely OUR app — no third-party service. The only outbound calls are the
same APIs the CLI already uses (Anthropic, Loxo, Seamless). Host it anywhere that runs
Python (a laptop, a small VM, Render) and the whole team uses one URL — no terminal.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from fastapi import File, UploadFile

from emerald.boolean_filter import augment_boolean, candidate_text, filter_candidates
from emerald.config import settings
from emerald.fireflies import fetch_transcript, parse_client_name
from emerald.handshake import parse_applicants_csv, push_applicants
from emerald.pipeline import run_pipeline

app = FastAPI(title="Emerald", version="0.2.0")

# Simple shared-password gate on the web UI. Default "emerald"; override in the host
# env with EMERALD_UI_PASSWORD. (The browser will prompt for login — any username,
# this password.) /health is left open so Render's health check works.
UI_PASSWORD = os.getenv("EMERALD_UI_PASSWORD", "emerald")
_security = HTTPBasic()


def require_login(creds: HTTPBasicCredentials = Depends(_security)) -> bool:
    if not secrets.compare_digest(creds.password, UI_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# ----------------------------- webhook (hands-off path) -----------------------------
def _verify_fireflies_signature(raw_body: bytes, header: str | None) -> bool:
    """Verify the x-hub-signature (HMAC-SHA256) if a secret is configured."""
    if not settings.fireflies_webhook_secret:
        return True  # no secret set -> not enforced (dev)
    if not header:
        return False
    expected = hmac.new(
        settings.fireflies_webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    provided = header.split("=", 1)[1] if "=" in header else header
    return hmac.compare_digest(expected, provided)


def _transcript_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
    """Return (transcript_text, client_name) from a webhook payload.

    Fireflies sends {meetingId, eventType} -> fetch the transcript via GraphQL and
    derive the client from the meeting title. Other providers may post the transcript
    text inline -> use it directly.
    """
    meeting_id = payload.get("meetingId") or payload.get("meeting_id")
    if meeting_id:
        text, title = fetch_transcript(meeting_id)
        client = parse_client_name(title) or payload.get("client_name", "")
        return text, client
    # generic fallback (transcript inline)
    for key in ("transcript", "text", "transcript_text"):
        if isinstance(payload.get(key), str):
            client = payload.get("client_name") or payload.get("metadata", {}).get("client", "")
            return payload[key], client
    if isinstance(payload.get("data"), dict):
        return _transcript_from_payload(payload["data"])
    return "", ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/transcript")
async def on_transcript(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not _verify_fireflies_signature(raw, request.headers.get("x-hub-signature")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="invalid webhook signature")
    payload = json.loads(raw or b"{}")

    # Only act on "transcription completed"-type events (ignore other Fireflies events).
    event = (payload.get("eventType") or "").lower()
    if event and "complet" not in event and "transcri" not in event:
        return {"ok": True, "skipped": f"ignored event: {payload.get('eventType')}"}

    transcript, client = _transcript_from_payload(payload)
    if not transcript:
        return {"ok": False, "error": "no transcript found (or GraphQL fetch failed)"}

    result = run_pipeline(
        transcript,
        client_name=client,
        push_to_loxo=settings.webhook_push,  # EMERALD_WEBHOOK_PUSH=true to auto-create the job
    )
    return {
        "ok": True,
        "title": result["deliverables"].get("title"),
        "client": client,
        "job_url": (result.get("loxo") or {}).get("job_url"),
        "redaction_hits": result["redaction_hits"],
    }


# --------------------------------- web UI (browser) ---------------------------------
_PAGE = """<!doctype html><meta charset=utf-8><title>Emerald</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#1a2b22}}
 h1{{color:#2e7d52}} textarea{{width:100%;height:220px;padding:.6rem;font:13px monospace}}
 input[type=text]{{width:100%;padding:.5rem}} label{{display:block;margin:.6rem 0 .2rem;font-weight:600}}
 .row{{display:flex;gap:1.5rem;margin:.8rem 0}} .row label{{font-weight:400;margin:0}}
 button{{background:#2e7d52;color:#fff;border:0;padding:.7rem 1.4rem;border-radius:6px;font-size:15px;cursor:pointer}}
 pre{{background:#f4f7f5;padding:.8rem;border-radius:6px;overflow:auto;white-space:pre-wrap}}
 .card{{border:1px solid #d9e4dd;border-radius:8px;padding:1rem;margin:1rem 0}}
 a.job{{display:inline-block;background:#eaf5ee;padding:.5rem .8rem;border-radius:6px;text-decoration:none;color:#1b5e3a;font-weight:600}}
 .muted{{color:#6b7d72}}
</style>
<h1>Emerald</h1>
<p class=muted>Paste an intake-call transcript &rarr; anonymized JD, Booleans, Loxo job, sourced candidates.
&nbsp;·&nbsp; <a href="/search">🔎 Boolean Workbench &rarr;</a>
&nbsp;·&nbsp; <a href="/applicants">📥 Handshake applicants &rarr;</a></p>
<form method=post action=/run>
 <label>Client name (anonymized out)</label>
 <input type=text name=client placeholder="e.g. Merrymeeting Group">
 <label>Intake transcript</label>
 <textarea name=transcript placeholder="Paste the call transcript here...">{transcript}</textarea>
 <div class=row>
  <label><input type=checkbox name=push value=1 {push}> Create Loxo job</label>
  <label><input type=checkbox name=source value=1 {source}> Source + attach candidates (Seamless)</label>
 </div>
 <button>Run</button>
</form>
{results}
"""


def _esc(x: Any) -> str:
    return html.escape(str(x or ""))


def _render_results(result: dict[str, Any]) -> str:
    d = result.get("deliverables", {})
    parts = ['<div class=card>']
    parts.append(f"<h2>{_esc(d.get('title'))}</h2>")
    parts.append(f"<p class=muted>Job family: {_esc(result.get('job_type'))} · "
                 f"Redaction hits: {_esc(result.get('redaction_hits') or 'none')}</p>")
    loxo = result.get("loxo") or {}
    if loxo.get("job_url"):
        parts.append(f'<p><a class=job href="{_esc(loxo["job_url"])}" target=_blank>'
                     f'🔗 Open Loxo job</a></p>')
    parts.append("<h3>Job description</h3>")
    parts.append(f"<pre>{_esc(result.get('job_description_markdown'))}</pre>")
    parts.append("<h3>Boolean strings</h3><pre>")
    for k, v in (d.get("boolean_strings") or {}).items():
        parts.append(f"[{k}] {_esc(v)}\n")
    parts.append("</pre>")
    s = result.get("sourcing") or {}
    if s.get("candidates"):
        pushed = (s.get("pushed_to_loxo") or {}).get("created")
        head = f"<h3>Sourced candidates: {len(s['candidates'])}"
        if pushed is not None:
            head += f" · {pushed} added to Loxo"
        parts.append(head + "</h3><pre>")
        for c in s["candidates"][:50]:
            contact = f" · {_esc(c.get('email'))}" if c.get("email") else ""
            parts.append(f"• {_esc(c.get('name'))} — {_esc(c.get('title'))} @ "
                         f"{_esc(c.get('company'))}{contact}\n")
        parts.append("</pre>")
    elif s.get("error"):
        parts.append(f"<p class=muted>Sourcing: {_esc(s['error'])}</p>")
    parts.append("</div>")
    return "".join(parts)


@app.get("/", response_class=HTMLResponse)
def home(_: bool = Depends(require_login)) -> str:
    return _PAGE.format(transcript="", push="", source="", results="")


@app.post("/run", response_class=HTMLResponse)
def run(
    transcript: str = Form(""),
    client: str = Form(""),
    push: bool = Form(False),
    source: bool = Form(False),
    _: bool = Depends(require_login),
) -> str:
    if not transcript.strip():
        return _PAGE.format(transcript="", push="", source="",
                            results="<p class=muted>Please paste a transcript.</p>")
    result = run_pipeline(
        transcript,
        client_name=client,
        push_to_loxo=push or source,   # sourcing needs a job to attach to
        source=source,
        push_candidates=source,
    )
    return _PAGE.format(
        transcript=_esc(transcript),
        push="checked" if push else "",
        source="checked" if source else "",
        results=_render_results(result),
    )


# ------------------------------ Boolean Workbench (custom search) ------------------------------
# Swap out the recruiting Boolean / add search filters, and (optionally) test the result
# against a pasted candidate list — all local, no API keys, works fully offline. This exercises
# the same engine (emerald.boolean_filter) the pipeline uses to pre-screen sourced candidates.

_SEARCH_PAGE = """<!doctype html><meta charset=utf-8><title>Emerald · Boolean Workbench</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1a2b22}}
 h1{{color:#2e7d52}} textarea{{width:100%;padding:.6rem;font:13px monospace}}
 input[type=text]{{width:100%;padding:.5rem;font:13px sans-serif}} label{{display:block;margin:.7rem 0 .2rem;font-weight:600}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:0 1.2rem}} .hint{{font-weight:400;color:#6b7d72;font-size:12px}}
 button{{background:#2e7d52;color:#fff;border:0;padding:.7rem 1.4rem;border-radius:6px;font-size:15px;cursor:pointer;margin-top:.8rem}}
 pre{{background:#f4f7f5;padding:.8rem;border-radius:6px;overflow:auto;white-space:pre-wrap}}
 .card{{border:1px solid #d9e4dd;border-radius:8px;padding:1rem;margin:1rem 0}}
 .muted{{color:#6b7d72}} .kept{{color:#1b5e3a}} .dropped{{color:#a23a2f}}
 .composed{{background:#eaf5ee;border:1px solid #bcdcc8;padding:.7rem;border-radius:6px;font:13px monospace;white-space:pre-wrap}}
 code{{background:#f4f7f5;padding:0 .25rem;border-radius:3px}}
 select{{width:100%;padding:.45rem;font-size:13px;margin:.15rem 0 .35rem;color:#2e5c44}}
 .chips{{margin:.25rem 0 0}}
 .chip{{background:#eef4f0;border:1px solid #cfe0d6;border-radius:999px;padding:.1rem .6rem;font-size:12px;cursor:pointer;margin:.15rem .25rem 0 0;color:#2e5c44}}
 .chip.on{{background:#2e7d52;border-color:#2e7d52;color:#fff}}
</style>
<h1>Boolean Workbench</h1>
<p class=muted><a href="/">&larr; Back to Emerald</a> &nbsp;·&nbsp; Swap out a Boolean and layer on filters. Optionally paste candidates to see who survives.</p>
<form method=post action=/search>
 <label>Base Boolean <span class=hint>(pick a starter, paste a generated string, or leave blank to build from filters)</span></label>
 __STARTERS__
 <textarea name=base_boolean rows=3 placeholder='("Senior Accountant" OR Accountant) AND (GAAP OR SOX)'>{base_boolean}</textarea>
 <div class=grid>
  <div>
   <label>Must include — ALL of <span class=hint>(AND; comma-separated)</span></label>
   <input type=text name=include_all value="{include_all}" placeholder="CPA, month-end close">
   __CHIPS_ALL__
   <label>Must include — ANY of <span class=hint>(one OR-group; comma-separated)</span></label>
   <input type=text name=include_any value="{include_any}" placeholder="NetSuite, SAP, Oracle">
   __CHIPS_ANY__
  </div>
  <div>
   <label>Exclude <span class=hint>(NOT; comma-separated)</span></label>
   <input type=text name=exclude value="{exclude}" placeholder="intern, audit, recruiter">
   __CHIPS_EXCL__
   <label>Location <span class=hint>(AND'd on; phrase or OR-list)</span></label>
   <input type=text name=location value="{location}" placeholder='"New York" OR NY OR "New Jersey"'>
   __CHIPS_LOC__
  </div>
 </div>
 <label>Candidates to test <span class=hint>(optional — one per line, or a JSON list of objects)</span></label>
 <textarea name=candidates rows=6 placeholder="Jane Doe — Senior Accountant @ Acme · New York&#10;John Smith — Audit Intern @ BigCo · Boston">{candidates}</textarea>
 <button>Compose &amp; test</button>
</form>
{results}
<script>
function _parts(v){{return v.split(',').map(function(s){{return s.trim()}}).filter(Boolean)}}
function _sync(){{
 document.querySelectorAll('.chip').forEach(function(ch){{
  var have=_parts(document.forms[0][ch.dataset.f].value);
  var on=ch.dataset.v.split('|').every(function(v){{return have.indexOf(v)>=0}});
  ch.classList.toggle('on',on);
 }});
}}
document.addEventListener('click',function(e){{
 var ch=e.target.closest('.chip'); if(!ch)return;
 var f=document.forms[0][ch.dataset.f], have=_parts(f.value), vals=ch.dataset.v.split('|');
 var on=vals.every(function(v){{return have.indexOf(v)>=0}});
 if(on) have=have.filter(function(p){{return vals.indexOf(p)<0}});
 else vals.forEach(function(v){{if(have.indexOf(v)<0)have.push(v)}});
 f.value=have.join(', ');
 _sync();
}});
_sync();
</script>
"""

# Starter Booleans offered in the dropdown — lifted from the family exemplars in
# emerald/profiles.py (geography stripped out; that's what the Location field is for).
_STARTER_BOOLEANS: list[tuple[str, str]] = [
    ("Finance · Senior Accountant — corporate (not audit)",
     '("Senior Accountant" OR Accountant) AND (reconciliation* OR "journal entries" OR '
     '"month-end close") AND (Excel OR VLOOKUP OR "pivot tables") AND NOT (audit OR '
     'assurance OR auditor OR internship)'),
    ("Finance · Senior Accountant — from public accounting",
     '("Audit Associate" OR "Senior Auditor" OR "Assurance Senior" OR "Senior Associate") '
     'AND ("public accounting" OR "CPA firm" OR "Big 4") AND (GAAP OR GAAS OR '
     '"financial statement audits")'),
    ("Finance · Accounting Manager / Controller",
     '("Accounting Manager" OR "Senior Accountant" OR "Assistant Controller" OR Controller) '
     'AND ("internal controls" OR SOX OR GAAP OR CPA) AND ("month-end close" OR '
     '"financial statements" OR "general ledger")'),
    ("Finance · Investment Banking",
     '("Investment Banking Associate" OR "Transaction Advisory Associate" OR "M&A Associate")'),
    ("Tech · .NET Developer",
     'C# AND API AND SQL AND (Angular OR React OR Vue OR TypeScript)'),
    ("Tech · Network / Systems Engineer",
     '("systems engineer" OR "network engineer" OR "infrastructure engineer") AND '
     '("Windows Server" OR Hyper-V OR VMware) AND (SonicWall OR "Cisco Meraki" OR Ubiquiti '
     'OR firewall) AND NOT ("IT manager" OR "IT director" OR CTO OR "engineering manager" '
     'OR "team lead")'),
    ("Tech · SRE / DevOps",
     '("Site Reliability Engineer" OR SRE OR "DevOps Engineer") AND (AWS OR '
     '"Amazon Web Services" OR Azure)'),
    ("Tech · Data Scientist / ML",
     'Python AND SQL AND (PowerBI OR Tableau OR Alteryx) AND (ML OR "Machine Learning")'),
    ("Physician · Family / Internal Medicine",
     '("Primary Care Physician" OR "Internal Medicine Physician" OR "Family Medicine '
     'Physician") AND ("Board Certified" OR "Board Eligible" OR BC OR BE)'),
    ("Physician · Pulmonologist",
     '(Pulmonologist OR "Pulmonary Medicine" OR Pulmonary) AND ("Board Certified" OR '
     '"Board Eligible" OR BC OR BE OR BE/BC)'),
    ("Physician · OB/GYN",
     '(OB/GYN OR OBGYN OR "Obstetrics and Gynecology") AND ("Board Certified" OR '
     '"Board Eligible" OR BC OR BE)'),
    ("Lab · QC / Lab Technician",
     '("lab technician" OR "laboratory technician" OR "quality control technician" OR '
     'chemist) AND (coatings OR paint OR chemical OR chemistry OR laboratory OR testing) '
     'AND NOT (manager OR director OR supervisor)'),
]

# One-click preset chips per filter field. Each chip toggles its terms in/out of the
# field; '|' separates multiple terms (they land as comma-separated items, matching how
# augment_boolean splits the field). Location values are OR-fragments, so no commas/'|'.
_CHIPS: dict[str, list[tuple[str, str]]] = {
    "include_all": [
        ("CPA", "CPA"), ("GAAP", "GAAP"), ("SOX", "SOX"),
        ("Month-end close", "month-end close"), ("General ledger", "general ledger"),
        ("Excel", "Excel"), ("SQL", "SQL"), ("Board Certified", "Board Certified"),
        ("Bachelor's", "Bachelor*"),
    ],
    "include_any": [
        ("ERP (NetSuite/SAP/…)", "NetSuite|SAP|Oracle|Great Plains|Dynamics|QuickBooks"),
        ("BI (PowerBI/Tableau)", "PowerBI|Tableau|Alteryx"),
        ("Cloud (AWS/Azure)", "AWS|Azure|GCP"),
        ("Frontend (React/Angular…)", "React|Angular|Vue|TypeScript"),
        ("BC/BE", "Board Certified|Board Eligible|BC|BE"),
    ],
    "exclude": [
        ("Interns/students", "intern|internship|student"),
        ("Junior", "junior|entry level"),
        ("Audit/assurance", "audit|auditor|assurance"),
        ("Management", "manager|director|supervisor|VP|CTO|team lead"),
        ("Recruiters", "recruiter|talent acquisition"),
        ("Contract/freelance", "contractor|freelance"),
    ],
    "location": [
        ("Cleveland metro", 'Cleveland OR "Greater Cleveland" OR Akron OR "Cuyahoga County"'),
        ("Ohio", "Ohio OR OH"),
        ("NY tri-state", '"New York" OR NY OR "New Jersey" OR NJ OR Connecticut OR CT'),
        ("Remote", 'Remote OR "work from home" OR WFH'),
    ],
}


def _chips_html(field: str) -> str:
    btns = "".join(
        f'<button type=button class=chip data-f="{field}" data-v="{html.escape(v)}">'
        f"{html.escape(lbl)}</button>"
        for lbl, v in _CHIPS[field]
    )
    return f"<div class=chips>{btns}</div>"


def _starters_html() -> str:
    opts = "".join(
        f'<option value="{html.escape(b)}">{html.escape(lbl)}</option>'
        for lbl, b in _STARTER_BOOLEANS
    )
    return ('<select onchange="if(this.value)document.forms[0].base_boolean.value=this.value">'
            "<option value=''>— Starter Booleans (pick one to fill the box) —</option>"
            f"{opts}</select>")


# Bake the static presets into the page template once, at import time. (The __TOKENS__
# are plain .replace targets so the runtime .format() placeholders stay untouched.)
_SEARCH_PAGE = (
    _SEARCH_PAGE
    .replace("__STARTERS__", _starters_html())
    .replace("__CHIPS_ALL__", _chips_html("include_all"))
    .replace("__CHIPS_ANY__", _chips_html("include_any"))
    .replace("__CHIPS_EXCL__", _chips_html("exclude"))
    .replace("__CHIPS_LOC__", _chips_html("location"))
)


def _parse_candidates(text: str) -> list[dict[str, Any]]:
    """Turn the pasted candidates box into candidate dicts the filter can screen.

    Accepts a JSON list/object, or free-text lines (one candidate per line). A plain
    line is stored under `headline` so the whole line is searchable, and kept verbatim
    under `_raw` for display.
    """
    text = (text or "").strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return [c for c in data if isinstance(c, dict)]
        except json.JSONDecodeError:
            pass  # fall through to line parsing
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            out.append({"_raw": line, "headline": line})
    return out


def _cand_label(c: dict[str, Any]) -> str:
    if c.get("_raw"):
        return str(c["_raw"])
    bits = [c.get("name"), c.get("title"), f"@ {c['company']}" if c.get("company") else "",
            c.get("school"), c.get("major"),
            f"· {c['location']}" if c.get("location") else "",
            f"· {c['email']}" if c.get("email") else ""]
    return " ".join(str(b) for b in bits if b) or candidate_text(c) or "(candidate)"


def _render_search(composed: str, kept: list, dropped: list, tested: bool) -> str:
    parts = ["<div class=card>", "<h3>Composed Boolean</h3>",
             f"<div class=composed>{_esc(composed) or '<span class=muted>(empty)</span>'}</div>",
             "<p class=hint>Copy this into LinkedIn Recruiter, a Google X-ray, or Loxo Source. "
             "Add it as the pre-screen filter with <code>--filter</code> on the CLI.</p>"]
    if tested:
        parts.append(f"<h3>Results — <span class=kept>{len(kept)} kept</span>, "
                     f"<span class=dropped>{len(dropped)} dropped</span></h3>")
        if kept:
            parts.append("<p class=kept><b>Kept</b></p><pre>")
            parts += [f"✓ {_esc(_cand_label(c))}\n" for c in kept]
            parts.append("</pre>")
        if dropped:
            parts.append("<p class=dropped><b>Dropped</b></p><pre>")
            parts += [f"✗ {_esc(_cand_label(c))}\n" for c in dropped]
            parts.append("</pre>")
    parts.append("</div>")
    return "".join(parts)


# --------------------- Handshake applicants (CSV -> screen -> Loxo) ---------------------
# Handshake has no employer applicants API (ATS sync is Enterprise-only, no Loxo
# connector), so ingest is the per-job "Download Applicant Data (CSV)" export:
# upload/paste it here, Boolean-screen it, optionally push survivors onto a Loxo job.

_APPLICANTS_PAGE = """<!doctype html><meta charset=utf-8><title>Emerald · Handshake applicants</title>
<style>
 body{{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1a2b22}}
 h1{{color:#2e7d52}} textarea{{width:100%;padding:.6rem;font:13px monospace}}
 input[type=text]{{width:100%;padding:.5rem;font:13px sans-serif}} label{{display:block;margin:.7rem 0 .2rem;font-weight:600}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:0 1.2rem}} .hint{{font-weight:400;color:#6b7d72;font-size:12px}}
 button{{background:#2e7d52;color:#fff;border:0;padding:.7rem 1.4rem;border-radius:6px;font-size:15px;cursor:pointer;margin-top:.8rem}}
 pre{{background:#f4f7f5;padding:.8rem;border-radius:6px;overflow:auto;white-space:pre-wrap}}
 .card{{border:1px solid #d9e4dd;border-radius:8px;padding:1rem;margin:1rem 0}}
 .muted{{color:#6b7d72}} .kept{{color:#1b5e3a}} .dropped{{color:#a23a2f}} .err{{color:#a23a2f}}
 .row{{display:flex;gap:1.5rem;margin:.8rem 0}} .row label{{font-weight:400;margin:0}}
</style>
<h1>Handshake applicants</h1>
<p class=muted><a href="/">&larr; Back to Emerald</a> &nbsp;·&nbsp;
In Handshake open the job &rarr; Applicants &rarr; <b>Download Applicant Data (CSV)</b>, then upload it here.
Screen with a Boolean (build one in the <a href="/search">Workbench</a>) and push the keepers onto the Loxo job.</p>
<form method=post action=/applicants enctype=multipart/form-data>
 <label>Applicant CSV <span class=hint>(upload the Handshake export, or paste its contents below)</span></label>
 <input type=file name=csv_file accept=".csv,text/csv">
 <textarea name=csv_text rows=5 placeholder="First Name,Last Name,Email,School,Major,...">{csv_text}</textarea>
 <label>Screening Boolean <span class=hint>(matches ANY column of the export; blank = keep everyone)</span></label>
 <textarea name=boolean rows=2 placeholder='(Accounting OR Finance) AND (CPA OR "CPA eligible") AND NOT intern'>{boolean}</textarea>
 <div class=grid>
  <div>
   <label>Loxo job # <span class=hint>(the job the keepers get attached to)</span></label>
   <input type=text name=job_id value="{job_id}" placeholder="3621461">
  </div>
  <div>
   <div class=row style="margin-top:2.1rem">
    <label><input type=checkbox name=push value=1 {push}> Push kept applicants to Loxo</label>
   </div>
  </div>
 </div>
 <button>Screen{push_verb}</button>
</form>
{results}
"""


def _render_applicants(kept: list, dropped: list, boolean: str,
                       push_result: dict[str, Any] | None, push_error: str) -> str:
    parts = ["<div class=card>",
             f"<h3>Screened — <span class=kept>{len(kept)} kept</span>, "
             f"<span class=dropped>{len(dropped)} dropped</span>"
             f"{'' if boolean.strip() else ' <span class=hint>(no Boolean — kept everyone)</span>'}</h3>"]
    if push_result is not None:
        parts.append(f"<p class=kept><b>Pushed to Loxo: {push_result.get('created', 0)} "
                     f"added to the job pipeline.</b></p>")
        if push_result.get("errors"):
            parts.append("<p class=err><b>Push errors</b></p><pre>")
            parts += [f"! {_esc(e)}\n" for e in push_result["errors"]]
            parts.append("</pre>")
    if push_error:
        parts.append(f"<p class=err><b>{_esc(push_error)}</b></p>")
    if kept:
        parts.append("<p class=kept><b>Kept</b></p><pre>")
        parts += [f"✓ {_esc(_cand_label(c))}\n" for c in kept]
        parts.append("</pre>")
    if dropped:
        parts.append("<p class=dropped><b>Dropped</b></p><pre>")
        parts += [f"✗ {_esc(_cand_label(c))}\n" for c in dropped]
        parts.append("</pre>")
    parts.append("</div>")
    return "".join(parts)


@app.get("/applicants", response_class=HTMLResponse)
def applicants_form(_: bool = Depends(require_login)) -> str:
    return _APPLICANTS_PAGE.format(csv_text="", boolean="", job_id="", push="",
                                   push_verb="", results="")


@app.post("/applicants", response_class=HTMLResponse)
async def applicants_run(
    csv_text: str = Form(""),
    csv_file: UploadFile | None = File(None),
    boolean: str = Form(""),
    job_id: str = Form(""),
    push: bool = Form(False),
    _: bool = Depends(require_login),
) -> str:
    text = csv_text
    if csv_file and csv_file.filename:
        text = (await csv_file.read()).decode("utf-8-sig", errors="replace")
    applicants = parse_applicants_csv(text)
    if boolean.strip():
        kept, dropped = filter_candidates(applicants, boolean)
    else:
        kept, dropped = applicants, []

    push_result, push_error = None, ""
    if push and kept:
        if not job_id.strip():
            push_error = "Push skipped: enter the Loxo job # to attach the keepers to."
        else:
            try:
                push_result = push_applicants(kept, job_id.strip())
            except Exception as e:
                push_error = f"Push failed: {e}"

    results = ("<p class=muted>No applicants found — upload the Handshake CSV "
               "(or paste it) and try again.</p>" if not applicants
               else _render_applicants(kept, dropped, boolean, push_result, push_error))
    return _APPLICANTS_PAGE.format(
        csv_text=_esc(csv_text), boolean=_esc(boolean), job_id=_esc(job_id),
        push="checked" if push else "", push_verb=" &amp; push" if push else "",
        results=results,
    )


@app.get("/search", response_class=HTMLResponse)
def search_form(boolean: str = "", _: bool = Depends(require_login)) -> str:
    return _SEARCH_PAGE.format(base_boolean=_esc(boolean), include_all="", include_any="",
                               exclude="", location="", candidates="", results="")


@app.post("/search", response_class=HTMLResponse)
def search_run(
    base_boolean: str = Form(""),
    include_all: str = Form(""),
    include_any: str = Form(""),
    exclude: str = Form(""),
    location: str = Form(""),
    candidates: str = Form(""),
    _: bool = Depends(require_login),
) -> str:
    composed = augment_boolean(
        base=base_boolean, include_all=include_all, include_any=include_any,
        exclude=exclude, location=location,
    )
    cands = _parse_candidates(candidates)
    kept, dropped = filter_candidates(cands, composed) if cands else ([], [])
    return _SEARCH_PAGE.format(
        base_boolean=_esc(base_boolean), include_all=_esc(include_all),
        include_any=_esc(include_any), exclude=_esc(exclude), location=_esc(location),
        candidates=_esc(candidates),
        results=_render_search(composed, kept, dropped, tested=bool(cands)),
    )
