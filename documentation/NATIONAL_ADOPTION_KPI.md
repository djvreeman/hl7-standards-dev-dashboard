# Indicator 16: Countries with national adoption of HL7 specifications

## Purpose

Count countries adopting HL7 specifications (currently **FHIR-focused**) in national digital health initiatives—regulation, policy, government programs, or technical architectures.

## KPI formula (from 2026-T2 onward)

```text
KPI = | Survey(Mandated ∪ Advised FHIR)  ∪  Map(verified countries) |
```

Suggested `Notes` text:

> Results for FHIR only: union of {YEAR} State of FHIR Survey (regulation mandates or advises FHIR) and manually verified national evidence at https://danielvreeman.com/hl7-map/.

Anything confirmed in **either** source counts. The survey is a broad annual signal; the [map](https://danielvreeman.com/hl7-map/) / [Zotero HL7 Standards library](https://www.zotero.org/groups/5872416/hl7_standards/library) is the manually verified evidence base.

| Period | Value | Method (summary) |
|--------|------:|------------------|
| 2025-T1 | 23 | 2024 State of FHIR Survey |
| 2025-T2 | 28 | 2025 survey Mandated∪Advised (unique countries) |
| 2025-T3 | 34 | 2025 survey + early map increments |
| 2026-T2 | 46 | **Union** of 2026 survey Mandated∪Advised and map/Zotero country tags (incl. NZ verified outside survey) |

## Survey leg

**Question:** *Does the regulation specifically mention FHIR?*  
**Include** unique countries listed under **Yes, FHIR is mandated** or **Yes, FHIR is being advised**.

Rules:

1. Deduplicate to **countries**, not respondents.
2. If respondents from the same country contradict (`*`), count the country when **any** response is Mandated or Advised.
3. Do **not** use “any health-data regulation exists,” FHIR current-use scale, or national IG presence as the survey leg—those are related context, not this KPI’s survey definition.
4. After each annual report, copy the country lists into:

   - `data/raw/national-adoption/survey_fhir_regulation_{YEAR}.json`

## Map / Zotero leg

Verified countries are **country tags** on items in Zotero group `5872416` (plotted on the map).

- Topical tags (FHIR, Policy, Technical Framework, …) are excluded via `data/raw/national-adoption/zotero_non_country_tags.json`.
- When you manually confirm a country, tag the evidence item with the **country name** (and appropriate topical tags) so the next script run picks it up.
- Until Zotero reflects a confirmation, add the country to `data/raw/national-adoption/map_manual_countries.json` (and preferably a RIS import file under the same folder) so the KPI union does not wait on sync.
- Map URL: https://danielvreeman.com/hl7-map/

## Review queues (data collection)

The union under-counts true adoption only when evidence exists but is untagged; it over-counts if a survey claim is wrong. Use script outputs to prioritize work:

| Queue | Meaning | Action |
|-------|---------|--------|
| `priority_prior_survey_dropoff_not_on_map` | In prior survey Mandated/Advised, **absent** from current survey, **not** on map | Likely non-response—**focused manual review** and Zotero add if confirmed |
| `survey_only_not_on_map` | In current survey, not yet map-tagged | Verification backlog |
| Map-only | On map, not in current survey | Keep in KPI (union); no drop |

Do **not** remove a country from the KPI solely because it stopped appearing in the survey. Prefer verifying and tagging it on the map so the stock measure stays stable.

## Scripting

### Compute KPI + queues

```bash
python3 data/compute_national_adoption_kpi.py
# or explicitly:
python3 data/compute_national_adoption_kpi.py --survey-year 2026 --prior-survey-year 2025
```

Outputs under `data/processed/national-adoption/`:

| File | Contents |
|------|----------|
| `national_adoption_{YEAR}.json` | Full result: counts, country sets, suggested Notes |
| `national_adoption_union_{YEAR}.csv` | Union roster with `in_survey` / `in_map` flags |
| `national_adoption_review_queue_{YEAR}.csv` | Prioritized manual-review candidates |

Optional: `--zotero-api-key` if the group later requires auth for reads. `--prior-survey-year 0` skips drop-off analysis.

### Annual workflow

1. When the State of FHIR report is published, create `survey_fhir_regulation_{YEAR}.json` from the “Regulation mention FHIR” country lists.
2. Run `compute_national_adoption_kpi.py`.
3. Enter `kpi_value` and `kpi_notes` into `data/raw/all_kpis.csv` for the reporting period.
4. Work the review CSV: start with **priority drop-offs**, then survey-only backlog; add confirmed evidence + country tags in Zotero.
5. Re-run the script after Zotero updates if you want an updated union mid-cycle (e.g. T3 refresh).

### Extending later years

Only new inputs required:

1. New survey JSON extract.
2. Ongoing Zotero country tagging.
3. Update `zotero_non_country_tags.json` if new non-country tags appear.

No change to the union formula.

## Known caveats

- Survey coverage and respondents change year to year; drop-offs are usually **non-reporting**, not loss of adoption.
- The survey question is regulation-centric; policy/architecture-only countries (e.g. some map-only cases) may appear only via the map leg—that is intentional under the union rule.
- Indicator definition is broader than FHIR-only; Notes currently scope results to FHIR until multi-family evidence is systematically included.
- Country name spelling should match across survey JSON and Zotero tags (`Korea, Republic of`, etc.).
