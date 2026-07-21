"""Configuration loaded from environment (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv optional at import time
    pass


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    model: str = os.getenv("EMERALD_MODEL", "claude-sonnet-4-5")

    # Seamless.AI — candidate sourcing / contact enrichment (paid; API is Enterprise).
    seamless_api_key: str | None = os.getenv("SEAMLESS_API_KEY")

    # Fireflies.ai — live transcription. The webhook sends a meetingId; we fetch the
    # transcript via GraphQL. Secret verifies the x-hub-signature (HMAC-SHA256).
    fireflies_api_key: str | None = os.getenv("FIREFLIES_API_KEY")
    fireflies_webhook_secret: str | None = os.getenv("FIREFLIES_WEBHOOK_SECRET")
    # When true, the transcript webhook creates the Loxo job automatically (else it
    # only generates + saves the artifact). Keep false until you trust the flow.
    webhook_push: bool = os.getenv("EMERALD_WEBHOOK_PUSH", "false").lower() == "true"

    loxo_domain: str | None = os.getenv("LOXO_DOMAIN")
    loxo_slug: str | None = os.getenv("LOXO_SLUG")
    loxo_api_key: str | None = os.getenv("LOXO_API_KEY")
    loxo_default_job_type_id: str | None = os.getenv("LOXO_DEFAULT_JOB_TYPE_ID")
    loxo_default_company_id: str | None = os.getenv("LOXO_DEFAULT_COMPANY_ID")
    loxo_default_owner_id: str | None = os.getenv("LOXO_DEFAULT_OWNER_ID")
    # Job "belongs to" wiring. Loxo assigns a job owner by USER EMAIL (array),
    # not by id — see the jobs_create schema's job[owner_emails][]. Comma-separate
    # for co-owners. These must be Loxo login emails (discover via users_index).
    loxo_default_owner_emails_raw: str | None = os.getenv("LOXO_DEFAULT_OWNER_EMAILS")
    # Activity type used to post the sourcing brief as a job note. Discover IDs
    # via client.activity_types(); leave unset to skip posting the note on --push.
    loxo_note_activity_type_id: str | None = os.getenv("LOXO_NOTE_ACTIVITY_TYPE_ID")
    # Activity type used to place a sourced candidate on a job (a workflow-stage
    # activity). Defaults to this account's "Sourced" type; override per account.
    loxo_sourced_activity_type_id: str = os.getenv("LOXO_SOURCED_ACTIVITY_TYPE_ID", "87305")

    # ---- B1 pipeline / handoff config (names must match your Loxo workflow) ----
    # Defaults match the live Emerald Resource Group Loxo workflow: the full
    # long list lands on "Long List" (free), the shortlist on "Short List"
    # (where enrichment + outreach automations fire — the cost-control gate).
    sourcing_stage_name: str = os.getenv("LOXO_SOURCING_STAGE_NAME", "Long List")
    outreach_stage_name: str = os.getenv("LOXO_OUTREACH_STAGE_NAME", "Short List")
    outreach_campaign_name: str = os.getenv(
        "LOXO_OUTREACH_CAMPAIGN_NAME", "Confidential Outreach"
    )
    enrich_top_n: int = int(os.getenv("EMERALD_ENRICH_TOP_N", "20"))

    @property
    def loxo_default_owner_emails(self) -> list[str]:
        raw = self.loxo_default_owner_emails_raw
        return [e.strip() for e in raw.split(",") if e.strip()] if raw else []

    @property
    def loxo_base_url(self) -> str | None:
        if not (self.loxo_domain and self.loxo_slug):
            return None
        # NOTE: the Open API lives under /api/{slug}.  Do NOT use /api/v1/...
        # (that path is not part of the Open API and returns 403).
        return f"https://{self.loxo_domain}/api/{self.loxo_slug}"

    @property
    def has_seamless(self) -> bool:
        return bool(self.seamless_api_key)

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_loxo(self) -> bool:
        return bool(self.loxo_base_url and self.loxo_api_key)


settings = Settings()
