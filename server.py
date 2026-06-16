"""Optional webhook receiver: transcription provider -> Emerald pipeline.

Point your transcription vendor's "transcript ready" webhook (Recall.ai,
AssemblyAI, Fireflies, etc.) at POST /webhook/transcript. Adapt `extract_*` to
your provider's payload shape.

Run:  uvicorn server:app --reload --port 8000
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request

from emerald.pipeline import run_pipeline

app = FastAPI(title="Emerald", version="0.1.0")


def extract_transcript(payload: dict[str, Any]) -> str:
    # TODO: map to your provider. Common shapes shown as fallbacks.
    for key in ("transcript", "text", "transcript_text"):
        if isinstance(payload.get(key), str):
            return payload[key]
    if isinstance(payload.get("data"), dict):
        return extract_transcript(payload["data"])
    return ""


def extract_client_name(payload: dict[str, Any]) -> str:
    return payload.get("client_name") or payload.get("metadata", {}).get("client", "")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/transcript")
async def on_transcript(request: Request) -> dict[str, Any]:
    payload = await request.json()
    transcript = extract_transcript(payload)
    if not transcript:
        return {"ok": False, "error": "no transcript found in payload"}

    # NOTE: do real generation async in production (queue it); inline for the starter.
    result = run_pipeline(
        transcript,
        client_name=extract_client_name(payload),
        push_to_loxo=False,  # flip to True once IDs are configured + you trust the gate
    )
    return {
        "ok": True,
        "title": result["deliverables"].get("title"),
        "artifact": result.get("artifact_path"),
        "redaction_hits": result["redaction_hits"],
    }
