"""Job-type profiles: family-specific Boolean guidance, ad platforms, and exemplars.

Each profile tailors the generation prompt to a role family. The selected profile's
block is injected into the system prompt in generate.py. Add a new family by adding a
dict entry here — no core code changes needed. Profiles are derived from real Emerald
job orders / Boolean strings.

Selection: pass an explicit job_type, or let detect_profile() auto-classify from the
transcript. Unknown / low-signal → "general".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    keywords: tuple[str, ...]      # lowercased substrings used for auto-detection
    ad_platforms: tuple[str, ...]  # which of linkedin/indeed/doccafe to fill
    boolean_guidance: str
    exemplars: str


_PHYSICIAN = Profile(
    key="physician",
    label="Physician / Clinical",
    keywords=(
        "physician", " md ", " do ", "board certified", "board eligible", "bc/be",
        "be/bc", "pulmonolog", "ob/gyn", "obgyn", "obstetrics", "internal medicine",
        "family medicine", "primary care", "cardiolog", "psychiatr", "hospitalist",
        "dea", "medical license", "cme", "clinician", "outpatient panel",
    ),
    ad_platforms=("linkedin", "indeed", "doccafe"),
    boolean_guidance=(
        "Build: (specialty title synonyms) AND (\"Board Certified\" OR \"Board "
        "Eligible\" OR BC OR BE OR BE/BC) AND (geography as an OR-list of the states, "
        "cities, or counties in scope). Put license + DEA in requirements, not the "
        "Boolean. Geography may be states (e.g., \"New York\" OR NY OR \"New Jersey\" "
        "OR NJ) or a metro's city/county OR-list (Westchester OR \"White Plains\" OR "
        "Yonkers ...)."
    ),
    exemplars=(
        "[Family/Internal Medicine] (\"Primary Care Physician\" OR \"Internal Medicine "
        "Physician\" OR \"Family Medicine Physician\") AND (\"Board Certified\" OR "
        "\"Board Eligible\" OR BC OR BE) AND (\"New York\" OR NY OR \"New Jersey\" OR NJ "
        "OR Connecticut OR CT)\n"
        "[Pulmonologist] (Pulmonologist OR \"Pulmonary Medicine\" OR Pulmonary) AND "
        "(\"Board Certified\" OR \"Board Eligible\" OR BE OR BC OR BE/BC) AND "
        "(Connecticut OR CT OR \"New York\" OR NY OR \"New Jersey\" OR NJ)\n"
        "[OB/GYN] (OB/GYN OR OBGYN OR \"Obstetrics and Gynecology\") AND (\"Board "
        "Certified\" OR \"Board Eligible\" OR BE OR BC OR BE/BC) AND (Westchester OR "
        "\"White Plains\" OR Rye OR Yonkers OR \"New Rochelle\" OR Scarsdale)\n"
        "JD format: practice-focused sections (\"What your practice looks like\", \"Why "
        "physicians make the move\", \"Compensation & Benefits\"); lead comp with "
        "earning potential (e.g., \"$400K+ earning potential, base + productivity "
        "incentives\"); include CME, malpractice, schedule/call, referral/support."
    ),
)

_FINANCE = Profile(
    key="finance",
    label="Finance / Accounting",
    keywords=(
        "accountant", "accounting", "controller", "general ledger", "gaap", "gaas",
        "sox", " cpa", "month-end close", "reconciliation", "journal entries",
        "financial statements", "investment banking", "fp&a", "audit", "auditor",
        "assurance", "bookkeep",
    ),
    ad_platforms=("linkedin", "indeed"),
    boolean_guidance=(
        "Build: (title synonyms: \"Senior Accountant\" OR Accountant OR \"Accounting "
        "Manager\" OR Controller OR \"Assistant Controller\") AND (accounting skills: "
        "\"general ledger\" OR GL OR GAAP OR SOX OR reconciliations OR \"month-end "
        "close\" OR \"journal entries\" OR \"financial statements\") AND (Excel/ERP: "
        "Excel OR NetSuite OR SAP OR \"Great Plains\" OR Dynamics). "
        "EXCLUSIONS ARE CASE-DEPENDENT: add NOT (audit OR auditor OR assurance OR intern "
        "OR internship OR \"Big 4\") when targeting CORPORATE/operational accounting; "
        "but INSTEAD INCLUDE public-accounting titles (\"Audit Associate\" OR \"Senior "
        "Auditor\" OR \"Assurance Senior\") when the client wants candidates coming FROM "
        "public accounting. CPA optional unless stated. For investment banking, go "
        "title-led (\"Investment Banking Associate\" OR \"Transaction Advisory "
        "Associate\" OR \"M&A Associate\")."
    ),
    exemplars=(
        "[Corporate Senior Acct — NOT audit] (\"Senior Accountant\" OR Accountant) AND "
        "(reconciliation* OR \"journal entries\" OR \"month-end close\") AND (Excel OR "
        "VLOOKUP OR \"pivot tables\") AND (\"Bachelor's\" OR Accounting) AND NOT (audit "
        "OR assurance OR auditor OR internship)\n"
        "[Senior Acct FROM public accounting] (\"Audit Associate\" OR \"Senior Auditor\" "
        "OR \"Assurance Senior\" OR \"Senior Associate\") AND (\"public accounting\" OR "
        "\"CPA firm\" OR \"Big 4\") AND (GAAP OR GAAS OR \"financial statement audits\")\n"
        "[Accounting Manager] (\"Accounting Manager\" OR \"Senior Accountant\" OR "
        "\"Assistant Controller\" OR Controller) AND (\"internal controls\" OR SOX OR "
        "GAAP OR CPA) AND (\"month-end close\" OR \"financial statements\" OR \"general "
        "ledger\")\n"
        "[Investment Banking] (\"Investment Banking Associate\" OR \"Transaction "
        "Advisory Associate\" OR \"M&A Associate\")\n"
        "JD format: \"What You'll Be Doing\" / \"What We're Looking For\" / \"Why "
        "Consider This Opportunity\". Tailor the Indeed copy to also suit "
        "eFinancialCareers norms. No DocCafe."
    ),
)

_TECH = Profile(
    key="tech",
    label="Technology / Engineering",
    keywords=(
        "developer", "software engineer", ".net", " c#", "java", "python", " sql",
        "devops", "site reliability", " sre", "aws", "azure", "network engineer",
        "systems engineer", "systems administrator", "architect", "react", "angular",
        "machine learning", " ml ", "data scientist", "data engineer", "etl",
        "full stack", "back end", "front end", "kubernetes", "cisco",
    ),
    ad_platforms=("linkedin", "indeed"),
    boolean_guidance=(
        "Build SKILL-led: (title synonyms) AND (the required stack, joined by AND, with "
        "OR-groups for interchangeable tech) AND optionally (degree). Lead with the "
        "concrete stack the client named — languages, frameworks, cloud, DBs, tools. "
        "Use OR-groups like (Angular OR React OR Vue OR TypeScript), (Azure OR AWS), "
        "(PowerBI OR Tableau). EXCLUDE management: NOT (\"IT manager\" OR \"IT "
        "director\" OR \"VP\" OR \"CTO\" OR \"engineering manager\" OR \"team lead\"). "
        "Put hard constraints (US Citizen / Green Card, local-only, clearance) in "
        "requirements, NOT the Boolean."
    ),
    exemplars=(
        "[.NET] C# AND API AND SQL AND (Angular OR React OR Vue OR TypeScript) AND "
        "\"Bachelor of Science\"\n"
        "[Senior Network/Systems Eng] (\"systems engineer\" OR \"network engineer\" OR "
        "\"infrastructure engineer\") AND (\"Windows Server\" OR \"Hyper-V\" OR VMware) "
        "AND (SonicWall OR \"Cisco Meraki\" OR Ubiquiti OR firewall) NOT (\"IT "
        "manager\" OR \"IT director\" OR CTO OR \"engineering manager\" OR \"team "
        "lead\")\n"
        "[SRE/DevOps] (\"Site Reliability Engineer\" OR SRE OR \"DevOps Engineer\") AND "
        "(AWS OR \"Amazon Web Services\")\n"
        "[Architect] (\"Software Architect\" OR \"Principal Architect\" OR \"Enterprise "
        "Architect\" OR \"Solutions Architect\")\n"
        "[Data Scientist/ML] Python AND SQL AND (PowerBI OR Tableau OR Alteryx OR SSRS) "
        "AND (ML OR \"Machine Learning\")\n"
        "[SQL Engineer] SQL AND Data AND ETL AND \"Bachelor of Science\" AND (PowerBI OR "
        "Tableau)\n"
        "JD format: concise summary then Required / Preferred skills lists; honor "
        "citizenship/location constraints. Tailor Indeed copy to also suit Dice. No "
        "DocCafe."
    ),
)

_LAB = Profile(
    key="lab",
    label="Lab / Quality-Control Technician",
    keywords=(
        "lab technician", "laboratory technician", "quality control", "qc technician",
        "chemist", "coatings", "calibration", "sample prep", "assay", "wet lab",
    ),
    ad_platforms=("linkedin", "indeed"),
    boolean_guidance=(
        "Build: (title synonyms: \"lab technician\" OR \"laboratory technician\" OR "
        "\"quality control technician\" OR \"QC technician\" OR chemist) AND (industry / "
        "domain terms: e.g., coatings OR paint OR chemical OR chemistry OR testing OR "
        "laboratory) NOT (manager OR director OR supervisor). Keep it broad on title, "
        "narrow on the industry/domain the client works in."
    ),
    exemplars=(
        "[Lab Technician — coatings] (\"lab technician\" OR \"laboratory technician\" OR "
        "\"quality control technician\" OR chemist) AND (coatings OR paint OR chemical "
        "OR chemistry OR laboratory OR testing) NOT (manager OR director OR "
        "supervisor)\n"
        "JD format: \"Position Overview\" / \"Key Responsibilities\" / "
        "\"Qualifications\". Associate/Bachelor's in a science; SOP/safety emphasis. No "
        "DocCafe."
    ),
)

_GENERAL = Profile(
    key="general",
    label="General",
    keywords=(),
    ad_platforms=("linkedin", "indeed", "doccafe"),
    boolean_guidance=(
        "Build: (title synonyms) AND (the key skills/credentials grouped in OR-clauses) "
        "AND (geography if location-bound), and use NOT(...) to exclude obvious "
        "mismatches (wrong seniority, interns, adjacent-but-wrong roles). Expand "
        "credentials and enumerate geography as OR-lists."
    ),
    exemplars=(
        "Lead the Boolean with role title synonyms, AND the must-have skills/credentials "
        "the transcript names, AND geography when relevant; exclude clear mismatches "
        "with NOT(...). Only produce DocCafe ad copy if the role is clinical."
    ),
)

PROFILES: dict[str, Profile] = {
    p.key: p for p in (_PHYSICIAN, _FINANCE, _TECH, _LAB, _GENERAL)
}


def get_profile(key: str | None) -> Profile:
    """Return the named profile, or General if unknown/None."""
    if key and key.lower() in PROFILES:
        return PROFILES[key.lower()]
    return PROFILES["general"]


def detect_profile(text: str, title: str = "") -> Profile:
    """Auto-classify a transcript into a job family by keyword scoring.

    Title is weighted heavier than the body. Ties / no signal → General.
    """
    hay = f" {(title + ' ') * 3}{text} ".lower()
    best_key, best_score = "general", 0
    for key, prof in PROFILES.items():
        if key == "general":
            continue
        score = sum(hay.count(kw) for kw in prof.keywords)
        if score > best_score:
            best_key, best_score = key, score
    return PROFILES[best_key]
