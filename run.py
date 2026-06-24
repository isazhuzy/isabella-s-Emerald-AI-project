#!/usr/bin/env python3
"""Emerald CLI — run the Phase 1 pipeline on a transcript file.

Examples:
    python run.py examples/sample_transcript.txt
    python run.py examples/sample_transcript.txt --client "Acme Health System"
    python run.py examples/sample_transcript.txt --client "Acme Health" --push
"""
from __future__ import annotations

import argparse
import json
import sys

from emerald.config import settings
from emerald.pipeline import run_pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description="Emerald intake -> deliverables pipeline")
    ap.add_argument("transcript", help="Path to a transcript .txt file")
    ap.add_argument("--client", default="", help="Client/employer name to anonymize")
    ap.add_argument("--push", action="store_true", help="Create the job in Loxo (unpublished)")
    ap.add_argument("--publish", action="store_true",
                    help="Publish the job live on the careers page (implies --push). "
                         "Confidential JD is already anonymized; review first.")
    ap.add_argument("--quiet", action="store_true", help="Print only the artifact path")
    args = ap.parse_args()

    # --publish can't happen without creating the job first, so it implies --push.
    push = args.push or args.publish

    with open(args.transcript, encoding="utf-8") as f:
        transcript = f.read()

    if not settings.has_claude:
        print("⚠️  ANTHROPIC_API_KEY not set — using MOCK generation.\n", file=sys.stderr)
    if push and not settings.has_loxo:
        print("✖  --push/--publish requested but Loxo isn't configured (see .env.example).", file=sys.stderr)
        return 2

    result = run_pipeline(
        transcript, client_name=args.client, push_to_loxo=push, publish=args.publish
    )

    if args.quiet:
        print(result.get("artifact_path", ""))
        return 0

    d = result["deliverables"]
    print("=" * 64)
    print(f"TITLE: {d.get('title')}")
    print(f"Mock generation: {result['used_mock_generation']}  |  "
          f"Redaction hits: {result['redaction_hits'] or 'none'}")
    print("=" * 64)
    print("\n--- ANONYMIZED JD (markdown) ---\n")
    print(result["job_description_markdown"])
    print("\n--- BOOLEAN STRINGS ---")
    for k, v in d.get("boolean_strings", {}).items():
        print(f"  [{k}] {v}")
    print("\n--- AD COPY (platforms) ---")
    for k in ("linkedin", "indeed", "doccafe"):
        if k in d.get("ad_copy", {}):
            print(f"  [{k}] {d['ad_copy'][k][:120]}...")
    print(f"\n--- OUTREACH: {len(d.get('outreach', []))} steps ---")
    if result.get("loxo"):
        loxo = result["loxo"]
        if loxo.get("job_url"):
            state = "PUBLISHED" if args.publish else "unpublished"
            print(f"\n🔗 Loxo job ({state}): {loxo['job_url']}")
        else:
            print(f"\nLoxo: {json.dumps(loxo)[:300]}")
    print(f"\n📄 Full artifact:  {result.get('artifact_path')}")
    print(f"📋 Sourcing brief: {result.get('brief_path')}")
    print("   → hand this to the recruiter; see LOXO_SETUP.md for the one-time"
          " Stage Automation config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
