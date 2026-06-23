# Emerald — Live Demo Script (for presentation)

A 5–7 minute live demo of the intake-call → Loxo automation. Everything runs from the
`emerald/` folder.

## Before the room (prep — 2 min)
1. Open a terminal in the project: `cd ~/emerald`
2. Confirm config is loaded (no secrets printed):
   ```bash
   python3 -c "from emerald.config import settings; print('Claude:', settings.has_claude, '| Loxo:', settings.has_loxo)"
   ```
   Expect: `Claude: True | Loxo: True`
3. Have two browser tabs ready: your **Loxo Jobs** list, and the **careers page**
   (`app.loxo.co/emerald-resource-group`).
4. (Safety net) If the venue Wi-Fi is flaky, you can still demo generation offline —
   see "Fallback" below.

## The demo (talk + type)

**1. Frame it (15s):** "We take an intake-call transcript and, in one command, produce a
confidential job description, ad copy, outreach, Boolean strings — and create the job in
Loxo. No client name ever leaks."

**2. Show the input (20s):** open a transcript so they see it's just a call.
```bash
cat transcripts/merrymeeting-senior-accountant.txt
```

**3. Run it — preview first (90s):**
```bash
./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group"
```
Point out, on screen:
- The **anonymized JD** — "notice 'Merrymeeting Group' became 'an entrepreneurial,
  multi-industry holding company' — fully confidential."
- The **Why Join** section — "matches our house style."
- The **Boolean strings** — "credential expansions, the Cleveland-metro geography, and
  `NOT (audit OR auditor…)` exclusions, just like a recruiter would write."

**4. Create the job in Loxo — the payoff (90s):**
```bash
./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group" --push
```
Then in the browser:
- Open the new job in **Loxo → Jobs** → show it's **Unpublished** (review before live),
  company assigned, salary set.
- Open the job's **Overview/Notes** → show the **Sourcing Brief** posted as a note —
  "this is the recruiter's runbook: the Boolean to paste per channel and the target stages."

**5. Close (20s):** "From a call to a confidential, ready-to-source job in Loxo in under a
minute. The recruiter just runs the search and reviews — everything else is generated."

## Optional flourishes
- Show the previously-created **job #3621461** to prove it's repeatable.
- Mention `--publish` puts the (already-anonymized) listing **live on the careers page**
  in the same command.
- Show `output/` — every run saves a full JSON artifact + the brief markdown.

## Fallback (no/спotty internet)
Generation needs the Claude API; Loxo push needs Loxo. If offline:
- Run **mock mode** to show the pipeline shape without API calls:
  ```bash
  ANTHROPIC_API_KEY= python3 run.py examples/sample_transcript.txt --client "Acme Health System"
  ```
  (Prints a clearly-labeled MOCK package — good enough to show the flow.)
- Or pre-run step 3 & 4 beforehand and show the saved files in `output/`.

## One-liners to memorize
- Preview: `./emerald.sh transcripts/merrymeeting-senior-accountant.txt "Merrymeeting Group"`
- Push:    `… "Merrymeeting Group" --push`
- Publish: `… "Merrymeeting Group" --publish`  *(goes live on careers page — use intentionally)*
