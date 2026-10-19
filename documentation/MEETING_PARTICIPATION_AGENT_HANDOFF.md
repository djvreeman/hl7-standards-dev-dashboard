# Meeting participation → dashboard handoff

**Audience:** Agents working in `hl7-standards-dev-dashboard`  
**From:** Data ETL in sibling repo `hl7-standards-dev-data` (minutes-participation pipeline)  
**Status:** ETL complete for mapped WG spaces (run `9fcea8fc5652`, 2026-10-08). Dashboard JSON copied into `data/standards-development/`. Wire UI against the artifact contracts below.  
**Date:** 2026-10-08

Use this sheet when adding a **People / meeting participation** block to Work Group Health (or `/wg-health-history`). Match existing dashboard patterns in this repo; do not invent a parallel design system.

---

## 1. What was built (data side)

A Confluence-based monitor that:

1. Discovers meeting-minutes pages per WG space (telecon **and** WGM trees — one meeting population).
2. Caches **full page text** (no attachments) in SQLite.
3. Extracts attendance: **co-chairs + participants**, **organization** when reported.
4. Parses meeting dates from free-text titles (with confidence).
5. Emits dashboard-shaped JSON (same spirit as `wg_ballot_specs_matrix.json`).

| | Path |
| --- | --- |
| **ETL repo** | `../hl7-standards-dev-data` |
| **Pipeline** | `scripts/workgroup-health/minutes_participation/` |
| **Space map** | `data/config/wg-confluence-space-keys.yaml` (product WGs + selected MG spaces) |
| **Working outputs** | `data/working/process-documents/workgroup-health/minutes-participation/` |
| **SQLite cache** | `…/minutes_participation/minutes_cache.sqlite` (local only; **do not** ship to dashboard) |
| **Plan** | Cursor plan `minutes_participation_monitor` / data-repo WG health docs |

**Out of scope for v1 UI:** Salesforce person join; Call Center “scheduled but no minutes”; shipping full minutes text to the browser; affiliates / EC / FHIR Director as separate WGs.

**Intentionally unmapped:** HTA (subgroup of TSMG), Publishing (deprecated).

---

## 2. Files to copy into this dashboard repo

After ETL finishes (or after `--reparse` + rollup), copy these into:

`data/standards-development/`

| Source file (data repo `minutes-participation/`) | Destination | Purpose |
| --- | --- | --- |
| `wg_meeting_participation.json` | same name | Portfolio KPIs per WG (primary) |
| `wg_meeting_participation_trimesters.json` | same name | WG × trimester heatmap/matrix |
| `wg_meeting_meetings.json` | same name | Per-meeting drill-down |
| `wg_meeting_people.json` | same name | Person index (optional secondary panel) |
| `wg_meeting_organizations.json` | same name | Org index (optional secondary panel) |

Optional QA (not required by API): `wg-meeting-participation-summary.md`, `wg-meeting-participation-gaps.md`.

**Do not copy:** `minutes_cache.sqlite`, page bodies, Confluence discovery JSON.

Mirror the runbook style in [`WG_HEALTH_HISTORY_UPDATE_RUNBOOK.md`](WG_HEALTH_HISTORY_UPDATE_RUNBOOK.md): offline JSON under `data/standards-development/`, service class + routes, no live Confluence calls from the dashboard.

---

## 3. Data contracts (read these carefully)

### 3.1 Null semantics

**Blank / missing = `null`, not zero.** Same rule as ballot matrix and WGH finals.

- WG with no Confluence space mapped → metric fields `null` (row still present).
- Trimester cell with no meetings → cell metrics `null`.
- Empty attendance section on a real meeting → meeting stays in series; `parse_status: "empty"`; do **not** treat as “zero people showed up” in the hero reading without showing coverage.

### 3.2 Stable join key

Use **`wg_key`** (WGH slug, e.g. `infrastructure-and-messaging`) to join:

- `wg_health_finals.json`
- `wg_ballot_specs_matrix.json`
- `wg_status.json`
- meeting participation JSON

Also available: `jira_key`, `space_key`, `wg_name`.

### 3.3 `wg_meeting_participation.json`

```json
{
  "meta": {
    "generated_at": "…",
    "window": { "type": "trailing_months", "months": 24, "as_of": "YYYY-MM-DD", "cutoff": "…" },
    "meeting_population": "wgm+telecon",
    "date_rule": "parsed meeting_date; unresolved excluded from window",
    "work_group_master": "JIRA-Spec-Artifacts workgroups + confluence space keys"
  },
  "workgroups": [
    {
      "wg_key": "infrastructure-and-messaging",
      "wg_name": "Infrastructure and Messaging",
      "jira_key": "inm",
      "space_key": "INM",
      "meetings_indexed": 95,
      "meetings_wgm": 3,
      "meetings_telecon": 92,
      "meetings_with_attendance": 77,
      "meetings_empty_attendance": 4,
      "meetings_unparseable": 10,
      "meetings_date_unresolved": 2,
      "median_headcount": 7.0,
      "median_participant_headcount": 4.0,
      "pct_meetings_ge_5": 1.0,
      "pct_quorum_met": 0.85,
      "distinct_people": 28,
      "distinct_participants": 22,
      "distinct_cochairs": 3,
      "pct_present_beyond_cochairs": 0.62,
      "pct_meetings_with_participant": 0.88,
      "distinct_organizations": 14,
      "pct_present_rows_with_org": 0.55,
      "coverage_score": 0.81,
      "last_meeting_date": "2026-09-30"
    }
  ]
}
```

Rates are **0–1 floats** (multiply by 100 for display).

### 3.4 `wg_meeting_participation_trimesters.json`

Same skeleton as `wg_ballot_specs_matrix.json`:

- `meta`, `trimesters[]`, `trimester_labels[]`, `rows[]`
- Each row: `wg_key`, `wg_name`, `cells[]`
- Each cell: `trimester`, `label`, `meetings`, `median_headcount`, `pct_meetings_ge_5`, `distinct_participants`, `pct_present_beyond_cochairs`, `coverage_score` (nullable)

### 3.5 `wg_meeting_meetings.json`

One object per **canonical** meeting (`meeting_uid` dedupe already applied in ETL):

- `page_id`, `wg_key`, `space_key`, `title`, `url`
- `meeting_date`, `meeting_date_confidence` (`high` \| `medium` \| `low` \| `unresolved`)
- `meeting_context` (`wgm` \| `telecon` \| `unknown`)
- `meeting_type` (`main` \| `project` \| `wgm` \| `other`) — from ConCalls match + title heuristics; WGM context always → `wgm`
- `concall_id`, `match_status` (`linked` \| `review` \| `unmatched_minutes`) when ConCalls overlay applied
- `headcount`, `cochair_count`, `participant_count`
- `quorum_met`, `parse_status` (`ok` \| `partial` \| `empty` \| `unparseable`)
- `distinct_orgs`

### 3.6 People / orgs (secondary)

- People: `wg_key`, `name_norm`, `display_name`, `role_primary`, `meetings_present`, `organizations_seen[]`, `last_seen_date`
- Orgs: `wg_key`, `organization_norm`, `display_name`, `meetings_represented`, `distinct_people`, `last_seen_date`

Names are **raw normalized strings**, not Salesforce Contacts.

---

## 4. Suggested UI (align with existing WG health page)

Preserve this repo’s established look (HL7 fonts/colors, existing `/wg-health-history` layout language). Prefer extending that page or a clear sibling route over a one-off microsite.

### Priority views

1. **Portfolio strip (People)** — KPI cards from summary JSON:
   - Median headcount  
   - % meetings with ≥5 present (`pct_meetings_ge_5`) — GOM-oriented signal  
   - % present beyond co-chairs (`pct_present_beyond_cochairs`)  
   - Coverage (`coverage_score`) as **data quality**, not health (tone: neutral/warning when low)

2. **WG ranking table** — sort by quiet signals (low `pct_meetings_ge_5` / low `distinct_participants`), join sunset markers from `wg_status.json` like other panels.

3. **Trimester heatmap** — reuse ballot-matrix interaction patterns; color by `median_headcount` or `pct_meetings_ge_5`.

4. **WG drill-down** — headcount over `meeting_date` from meetings JSON; optional stacked co-chair vs participant; WGM vs telecon as series or markers (`meeting_context`).

5. **Optional:** top organizations for selected WG; link out to Confluence via `url` / `page_id`.

### Readings to avoid

- Do not collapse “no minutes parseable” into “dead WG” without showing `coverage_score` / empty / unparseable counts.
- Do not mix **ballot** participation (enrolled / active voters) with **meeting** headcount in the same KPI without labeling both.
- Do not score handbook checklist items; this block answers “are calls attended beyond co-chairs?”

Strategic framing lives in the data repo:

`hl7-standards-dev-data/data/working/process-documents/workgroup-health/wg-health-vision-tsc-staff.md`  
`…/wg-health-master-data-plan.md` (conference call series + minutes attendees)

Mock direction (data repo, not production UI):

`…/workgroup-health/wg-health-dashboard-mockup.html`

---

## 5. Implementation sketch (match local conventions)

Follow patterns in:

- `app/wg_health_history_service.py`
- `app/wg_portfolio_matrices_service.py`
- `app/main.py` routes for `/wg-health-history`

Suggested shape:

1. `app/wg_meeting_participation_service.py` — load the five JSON files from `data/standards-development/`.
2. API routes, e.g.:
   - `GET /api/wg-meeting-participation/summary`
   - `GET /api/wg-meeting-participation/trimesters`
   - `GET /api/wg-meeting-participation/meetings?wg_key=`
   - `GET /api/wg-meeting-participation/people?wg_key=` (optional)
3. Template/JS panel on the WG health history page (or new nav entry consistent with existing IA).
4. Update `documentation/WG_HEALTH_HISTORY_UPDATE_RUNBOOK.md` with a short “Meeting participation” section pointing here + copy commands.

### Copy command (from dashboard repo root)

```bash
SRC="../hl7-standards-dev-data/data/working/process-documents/workgroup-health/minutes-participation"
DST="data/standards-development"
cp "$SRC"/wg_meeting_participation.json \
   "$SRC"/wg_meeting_participation_trimesters.json \
   "$SRC"/wg_meeting_meetings.json \
   "$SRC"/wg_meeting_people.json \
   "$SRC"/wg_meeting_organizations.json \
   "$DST"/
```

Re-copy after each successful ETL rollup (end of Confluence sync or `--reparse`).

---

## 6. How to refresh ETL (if agents need to re-run data)

Sibling repo `hl7-standards-dev-data`:

```bash
# Incremental Confluence sync (needs token in data/config/main.yaml or CONFLUENCE_TOKEN)
python scripts/workgroup-health/minutes_participation/run_minutes_participation.py \
  --main-config data/config/main.yaml \
  --all-mapped \
  --lookback-months 24

# Re-extract from cached page text only (no network)
python scripts/workgroup-health/minutes_participation/run_minutes_participation.py \
  --reparse --all-mapped --lookback-months 24
```

Unit tests:

```bash
python -m unittest discover -s scripts/workgroup-health/minutes_participation/tests -v
```

Pipeline README: `scripts/workgroup-health/minutes_participation/README.md`.

---

## 7. Acceptance checks for dashboard agents

- [ ] JSON loads offline from `data/standards-development/` (no Confluence/Jira calls).
- [ ] `wg_key` joins cleanly to ballot matrix / WGH finals / `wg_status`.
- [ ] `null` rendered as em dash / empty — never coerced to `0`.
- [ ] Coverage called out as data quality; ≥5 and beyond-co-chairs as participation signals.
- [ ] WGM + telecon not split into separate “health scores” (optional filter/breakdown only).
- [ ] Visual language matches existing WG health history page (fonts, colors, table/heatmap patterns).
- [ ] Runbook updated with copy steps.

---

## 8. Context pointers in this repo

| Resource | Why |
| --- | --- |
| [`WG_HEALTH_HISTORY_UPDATE_RUNBOOK.md`](WG_HEALTH_HISTORY_UPDATE_RUNBOOK.md) | Established ETL → copy → serve flow |
| `data/standards-development/wg_ballot_specs_matrix.json` | Matrix JSON shape to mirror |
| `app/wg_health_history_service.py` | Service loading pattern |
| `static/css/dashboard.css` + fonts setup docs | Brand/style constraints |
| Recent agent chat on WG health plan (Oct 2026) | Product direction already reviewed here |

When unsure about visual tone, **prefer matching `/wg-health-history`** over the data-repo HTML mockup.
