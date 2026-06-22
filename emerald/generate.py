"""Claude generation: intake transcript -> structured recruiting deliverables.

Returns a dict with these top-level keys (the contract the rest of the pipeline
relies on):

    title                 str   - role title (generic, no employer)
    jd                    dict  - anonymized JD: summary, responsibilities[], requirements[], why_join[]
    comp                  dict  - {min, max, currency, period}
    ad_copy               dict  - {linkedin, indeed, doccafe}  (platform-tailored)
    outreach              list  - sequence steps [{channel, day, subject, body}]
    boolean_strings       dict  - {generic, linkedin, google_xray, loxo_source}
    search_criteria       dict  - {titles[], skills[], location, seniority, must_have[], nice_to_have[]}
"""
from __future__ import annotations

import json
from typing import Any

from .config import settings

SYSTEM_PROMPT = """\
You are a senior recruiting operations assistant at Emerald Resource Group. From a
recruiter/hiring-manager intake-call transcript you produce a complete, ready-to-use
sourcing package.

HARD RULES:
- CONFIDENTIAL / ANONYMOUS output. Never name the employer, its products, named
  people, or an exact street address. Generalize identifying details
  (e.g. "a Series B fintech", "a regional health system"). Keep the role itself
  vivid and specific. (The style examples below name companies for format reference
  ONLY — your output must stay anonymous.)
- Tailor ad copy to each platform's norms: LinkedIn (concise, first-person,
  ~150 words), Indeed (structured, scannable, keyword-rich), DocCafe
  (physician/clinician audience — clinical setting, schedule, call, comp framing).
- Boolean strings must be syntactically valid and reusable. Provide platform
  variants (LinkedIn search, Google X-ray, and a Loxo Source friendly version).
- Output MUST be a single JSON object. No prose, no markdown fences.

JD WRITING STYLE (match Emerald's house style shown in the examples):
- Open with a short, energizing summary that frames the org generically and sells
  the opportunity (visibility, stability, culture, growth) — not a dry blurb.
- `responsibilities` = punchy, action-led bullets ("What You'll Be Doing").
- `requirements` = concrete, scannable must-haves ("What We're Looking For"):
  degree/credential, years of experience as a range, key skills/tools.
- `why_join` = 4-7 candidate-facing selling points ("Why Consider This
  Opportunity" / for clinicians "Why physicians make the move" + practice details):
  comp framing, benefits, autonomy, schedule, growth/partnership, culture.
- For physician/clinician roles, lead comp with earning potential
  (e.g. "$400K+ earning potential, base + productivity incentives") and include
  CME, malpractice, schedule/call, and referral/support details.

BOOLEAN QUALITY (match the examples):
- Expand certifications/credentials: ("Board Certified" OR "Board Eligible" OR BC
  OR BE OR BE/BC); ("Bachelor's" OR degree field).
- Enumerate geography as an OR-list of the metro/cities/states in scope.
- Group role titles and key skills in OR-clauses joined by AND.
- Use NOT to exclude obvious mismatches (e.g. NOT (intern OR resident OR locum)
  for clinicians; NOT (audit OR auditor OR assurance OR internship) for accounting).

JSON shape:
{
  "title": str,
  "jd": {"summary": str, "responsibilities": [str], "requirements": [str], "why_join": [str]},
  "comp": {"min": number|null, "max": number|null, "currency": "USD", "period": "year"},
  "ad_copy": {"linkedin": str, "indeed": str, "doccafe": str},
  "outreach": [{"channel": "email"|"inmail"|"sms", "day": int, "subject": str, "body": str}],
  "boolean_strings": {"generic": str, "linkedin": str, "google_xray": str, "loxo_source": str},
  "search_criteria": {"titles": [str], "skills": [str], "location": str,
                      "seniority": str, "must_have": [str], "nice_to_have": [str]}
}

STYLE EXAMPLES (Emerald house style — for STRUCTURE, TONE, and BOOLEAN shape only;
the employer names here are illustrative, keep YOUR output anonymous):

[Example A — Senior Accountant]
summary: entrepreneurial multi-industry organization, collaborative culture,
  high visibility to leadership, long-term growth.
responsibilities: Manage day-to-day accounting for assigned business units;
  Prepare and analyze monthly financial statements; General ledger maintenance
  and account reconciliations; Support month-end/year-end close; Maintain policies
  and internal controls; Assist annual audit preparation.
requirements: Bachelor's in Accounting; 4-8 years progressive accounting; Strong
  GL & financial reporting; Month-end close & reconciliations; Excel + ERP
  proficiency; Strong attention to detail.
why_join: Competitive compensation; Semi-annual bonus potential; Medical/dental/
  vision/401(k); High visibility; Collaborative culture; Long-term growth.
boolean: ("Senior Accountant" OR Accountant) AND (reconciliation* OR "journal
  entries" OR "month-end close") AND (AP OR "accounts payable") AND (AR OR
  "accounts receivable") AND (Excel OR VLOOKUP OR "pivot tables") AND ("Bachelor's"
  OR Accounting) AND NOT (audit OR assurance OR auditor OR internship)

[Example B — Pulmonologist]
why_join/practice: Established outpatient panel with immediate volume; No required
  hospital coverage; Predictable weekly schedule; Procedure flexibility; Strong
  internal referral network; Physician-led culture with autonomy; Long-term
  partnership potential.
comp: $400K+ earning potential; competitive base + productivity incentives; full
  benefits; CME allowance + PTO.
boolean: (Pulmonologist OR "Pulmonary Medicine" OR Pulmonary) AND ("Board
  Certified" OR "Board Eligible" OR BE OR BC OR BE/BC) AND (Connecticut OR CT OR
  "New York" OR NY OR "New Jersey" OR NJ)

[Example C — OB/GYN]
requirements: MD/DO; Board Certified or Board Eligible in OB/GYN; Active state
  license or ability to obtain; DEA license or eligibility.
why_join/practice: Established patient panel + immediate volume; Consistent
  multi-specialty referral network; Structured, predictable schedule; Physician-led
  autonomy; Partnership/ownership opportunity; CME + malpractice coverage.
boolean: (OB/GYN OR OBGYN OR "Obstetrics and Gynecology") AND ("Board Certified"
  OR "Board Eligible" OR BE OR BC OR BE/BC) AND (Westchester OR White Plains OR Rye
  OR Purchase OR Yonkers OR New Rochelle OR Scarsdale OR Harrison OR Tarrytown)
"""

USER_TEMPLATE = """\
Known client/employer name to anonymize away (never appears in output): {client_name}

Intake-call transcript:
\"\"\"
{transcript}
\"\"\"

Produce the JSON sourcing package now."""


def generate_deliverables(transcript: str, client_name: str = "") -> dict[str, Any]:
    """Call Claude and return the parsed deliverables dict.

    Falls back to a deterministic mock when ANTHROPIC_API_KEY is unset, so the
    pipeline is runnable offline for demos/tests.
    """
    if not settings.has_claude:
        return _mock_deliverables(transcript, client_name)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_content = USER_TEMPLATE.format(
        client_name=client_name or "(none provided)",
        transcript=transcript.strip(),
    )

    # The model occasionally emits invalid JSON (an unescaped quote in a long
    # field). Retry a couple of times before giving up — generation is variable,
    # so a fresh call usually parses. _parse_json strips any prose/fences.
    last_err: Exception | None = None
    for _ in range(3):
        resp = client.messages.create(
            model=settings.model,
            max_tokens=8000,
            # Prompt caching: the long system prompt is reused across every call,
            # so cache it to cut latency + cost on repeat runs.
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )
        raw = "".join(block.text for block in resp.content if block.type == "text")
        try:
            return _parse_json(raw)
        except json.JSONDecodeError as e:
            last_err = e
    raise RuntimeError(
        f"Claude returned unparseable JSON after 3 attempts: {last_err}"
    )


def _parse_json(raw: str) -> dict[str, Any]:
    """Tolerant JSON parse: strips ```json fences and trailing prose if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lstrip().startswith("json"):
            raw = raw.lstrip()[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _mock_deliverables(transcript: str, client_name: str) -> dict[str, Any]:
    """Offline placeholder so `python run.py` works without API keys."""
    return {
        "title": "Family Medicine Physician (Outpatient)",
        "jd": {
            "summary": (
                "A well-established regional health system is seeking a "
                "board-certified/board-eligible Family Medicine physician for a "
                "primarily outpatient role. (MOCK OUTPUT — set ANTHROPIC_API_KEY "
                "for real generation from the transcript.)"
            ),
            "responsibilities": [
                "Provide full-spectrum outpatient family medicine care",
                "Collaborate with a multidisciplinary care team",
                "Maintain accurate, timely documentation in the EHR",
            ],
            "requirements": [
                "MD or DO, board certified or board eligible in Family Medicine",
                "Active or eligible state medical license",
                "Strong outpatient clinical judgment and communication",
            ],
            "why_join": [
                "Competitive base salary plus productivity incentives",
                "Predictable outpatient schedule with light call",
                "Comprehensive benefits, CME allowance, and PTO",
                "Supportive, multidisciplinary, physician-led culture",
                "Long-term growth and partnership potential",
            ],
        },
        "comp": {"min": 230000, "max": 270000, "currency": "USD", "period": "year"},
        "ad_copy": {
            "linkedin": "Join a mission-driven care team as a Family Medicine "
            "physician — outpatient focus, strong support, competitive comp. (MOCK)",
            "indeed": "Family Medicine Physician — Outpatient\n• Board certified/eligible\n"
            "• Competitive base + benefits\n• Supportive, multidisciplinary team (MOCK)",
            "doccafe": "Outpatient Family Medicine opportunity with a regional health "
            "system. Predictable schedule, light call, comprehensive benefits. (MOCK)",
        },
        "outreach": [
            {"channel": "email", "day": 0, "subject": "Outpatient FM role — worth a look?",
             "body": "Hi {first_name}, I'm working a confidential outpatient Family "
             "Medicine search and your background stood out. Open to a quick chat? (MOCK)"},
            {"channel": "email", "day": 3, "subject": "Following up",
             "body": "Hi {first_name}, circling back on the FM opportunity — happy to "
             "share details on schedule and comp. (MOCK)"},
        ],
        "boolean_strings": {
            "generic": '("family medicine" OR "family practice") AND (physician OR MD OR DO) '
            'AND ("board certified" OR "board eligible") NOT (resident OR locum)',
            "linkedin": '("Family Medicine" OR "Family Practice") AND (Physician OR MD OR DO)',
            "google_xray": 'site:linkedin.com/in ("family medicine") (physician OR MD OR DO)',
            "loxo_source": "family medicine physician board certified outpatient",
        },
        "search_criteria": {
            "titles": ["Family Medicine Physician", "Primary Care Physician"],
            "skills": ["outpatient care", "EHR documentation", "preventive medicine"],
            "location": "(from transcript)",
            "seniority": "Attending",
            "must_have": ["BC/BE Family Medicine", "active/eligible license"],
            "nice_to_have": ["bilingual", "value-based care experience"],
        },
        "_mock": True,
    }
