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

from emerald.config import settings
from emerald.fireflies import fetch_transcript, parse_client_name
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
<p class=muted>Paste an intake-call transcript &rarr; anonymized JD, Booleans, Loxo job, sourced candidates.</p>
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
