#!/usr/bin/env bash
#
# Emerald wrapper — intake transcript -> recruiting package (-> Loxo).
#
#   ./emerald.sh <transcript.txt> "<Client Name>"          # preview only (no Loxo)
#   ./emerald.sh <transcript.txt> "<Client Name>" --push   # also create the unpublished Loxo job
#
# The client name is what gets ANONYMIZED OUT of every deliverable — it never
# appears in the JD, ad copy, or outreach.
#
set -euo pipefail

# Always run from the project root (where run.py and .env live), regardless of
# the directory you call this from.
cd "$(dirname "$0")"

if [ "$#" -lt 2 ]; then
  cat >&2 <<'USAGE'
Usage: ./emerald.sh <transcript.txt> "<Client Name>" [--push]

Examples:
  ./emerald.sh transcripts/merrymeeting-accountant.txt "Merrymeeting Group"
  ./emerald.sh transcripts/merrymeeting-accountant.txt "Merrymeeting Group" --push

Outputs land in ./output/ (a JSON package + a recruiter sourcing brief).
USAGE
  exit 1
fi

TRANSCRIPT="$1"
CLIENT="$2"
shift 2   # anything left over (e.g. --push) is passed straight through

if [ ! -f "$TRANSCRIPT" ]; then
  echo "Error: transcript file not found: $TRANSCRIPT" >&2
  exit 1
fi

exec python3 run.py "$TRANSCRIPT" --client "$CLIENT" "$@"
