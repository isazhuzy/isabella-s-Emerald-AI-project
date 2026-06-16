"""Deterministic anonymization safety-net.

The LLM is *instructed* to anonymize, but models occasionally leak an entity.
This pass scrubs known identifiers (client name, domains, named people) from the
generated deliverables as a belt-and-suspenders second layer. It runs over the
whole JSON blob so it catches leaks in any field.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

_DOMAIN_RE = re.compile(r"\b[\w.-]+\.(?:com|org|net|io|co|health|care|edu)\b", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")


def _variants(name: str) -> list[str]:
    """Generate name variants to catch (e.g. 'Acme Health' -> 'Acme', 'AcmeHealth')."""
    name = name.strip()
    if not name:
        return []
    out = {name, name.replace(" ", ""), name.replace(" ", "-")}
    parts = name.split()
    if len(parts) > 1:
        # Drop common suffixes so "Acme Health System" also masks "Acme".
        suffixes = {"inc", "inc.", "llc", "ltd", "corp", "co", "co.", "group",
                    "health", "system", "systems", "partners", "associates"}
        core = [p for p in parts if p.lower().strip(".,") not in suffixes]
        if core:
            out.add(core[0])
    return sorted((v for v in out if len(v) >= 3), key=len, reverse=True)


def redact(
    deliverables: dict[str, Any],
    client_name: str = "",
    extra_terms: Iterable[str] = (),
    mask: str = "the client",
) -> tuple[dict[str, Any], list[str]]:
    """Return (scrubbed_deliverables, list_of_terms_that_were_found_and_masked)."""
    blob = json.dumps(deliverables, ensure_ascii=False)
    hits: list[str] = []

    terms: list[str] = []
    terms += _variants(client_name)
    for t in extra_terms:
        terms += _variants(t)

    for term in sorted(set(terms), key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)
        if pattern.search(blob):
            hits.append(term)
            blob = pattern.sub(mask, blob)

    # Mask any leaked emails / web domains (but leave platform/JSON keys alone).
    if _EMAIL_RE.search(blob):
        hits.append("<email>")
        blob = _EMAIL_RE.sub("[redacted-email]", blob)

    scrubbed = json.loads(blob)
    return scrubbed, hits
