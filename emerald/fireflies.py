"""Fireflies.ai webhook helpers.

The Fireflies webhook is a NOTIFICATION — it sends {meetingId, eventType}, not the
transcript. We fetch the transcript via the GraphQL API using the meetingId, then
derive the client name from the meeting title (naming convention).

GraphQL: POST https://api.fireflies.ai/graphql  ·  Auth: Bearer <FIREFLIES_API_KEY>
"""
from __future__ import annotations

import re

import requests

from .config import settings

GRAPHQL_URL = "https://api.fireflies.ai/graphql"
_QUERY = (
    "query T($id: String!) { transcript(id: $id) "
    "{ title sentences { speaker_name text } } }"
)


def fetch_transcript(meeting_id: str) -> tuple[str, str]:
    """Fetch (transcript_text, meeting_title) for a Fireflies meetingId."""
    if not settings.fireflies_api_key:
        raise RuntimeError("FIREFLIES_API_KEY not set — cannot fetch the transcript.")
    resp = requests.post(
        GRAPHQL_URL,
        headers={
            "Authorization": f"Bearer {settings.fireflies_api_key}",
            "Content-Type": "application/json",
        },
        json={"query": _QUERY, "variables": {"id": meeting_id}},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(f"Fireflies GraphQL error: {body['errors']}")
    t = (body.get("data") or {}).get("transcript") or {}
    title = t.get("title") or ""
    lines: list[str] = []
    for s in t.get("sentences") or []:
        spk, txt = s.get("speaker_name") or "", s.get("text") or ""
        lines.append(f"{spk}: {txt}" if spk else txt)
    return "\n".join(lines), title


def parse_client_name(title: str) -> str:
    """Derive the client to anonymize from the meeting title.

    Convention: title the intake call "Intake — <Client>" (em dash, hyphen, or colon
    all work). Falls back to empty string, which just means no explicit redaction target.
    """
    if not title:
        return ""
    m = re.search(r"intake\s*[—:\-]\s*(.+)", title, re.I)
    return m.group(1).strip() if m else ""
