# WG Health Finals validation

Generated: 2026-10-16T01:57:02.182886+00:00
Status: **PASS**
Passed 13/14 (errors=0, warnings=1)

## Checks

- **PASS** `expected_cycles_present` — all 24 Final cycles present
- **PASS** `no_interim_sources` — no Interim PDFs in sources
- **PASS** `no_junk_wg_names` — no junk names
- **PASS** `no_acronym_prefixed_display_names` — display names normalized
- **PASS** `no_year_as_infraction` — no year-like infractions
- **PASS** `total_is_newest_t_column` — total_infractions == prior_period_infractions[0]
- **WARNING** `gold_star_usually_on_green` — 2019Sep clinical-interoperability-council: gold_star with band=yellow
- **PASS** `health_bands_match_legend` — green 0–3 / yellow 4–7 / red 8+
- **PASS** `no_duplicate_keys_per_cycle` — unique wg_key per cycle
- **PASS** `wg_count_sane` — 2019Jan:34, 2019May:33, 2019Sep:32, 2020Feb:31, 2020May:34, 2020Sep:33, 2021Jan:30, 2021May:30, 2021Sep:33, 2022Jan:33, 2022May:33, 2022Sep:33, 2023Jan:32, 2023May:32, 2023Sep:32, 2024Jan:32, 2024May:32, 2024Sep:32, 2025Jan:31, 2025May:31, 2025Sep:31, 2026Jan:31, 2026May:30, 2026Sep:30
- **PASS** `spot_checks` — all 8 spot checks passed
- **PASS** `period_labels` — all 4 period labels ok
- **PASS** `2026Sep_pdf_gold_stars` — wgs=30 gold=25 bands=['green'] no_star=['conformance', 'human-and-social-services', 'learning-health-systems', 'mobile-health', 'payer-provider-information-exchange'] non_green=none
- **PASS** `gold_star_timeline_present` — 2019Jan:17/34, 2019May:21/33, 2019Sep:17/32, 2020Feb:16/31, 2020May:17/34, 2020Sep:12/33, 2021Jan:17/30, 2021May:16/30, 2021Sep:26/33, 2022Jan:29/33, 2022May:25/33, 2022Sep:26/33, 2023Jan:26/32, 2023May:24/32, 2023Sep:27/32, 2024Jan:25/32, 2024May:27/32, 2024Sep:24/32, 2025Jan:21/31, 2025May:21/31, 2025Sep:24/31, 2026Jan:21/31, 2026May:15/30, 2026Sep:25/30

## Gold star timeline

- 2019Jan: 17 gold / 34 WGs
- 2019May: 21 gold / 33 WGs
- 2019Sep: 17 gold / 32 WGs
- 2020Feb: 16 gold / 31 WGs
- 2020May: 17 gold / 34 WGs
- 2020Sep: 12 gold / 33 WGs
- 2021Jan: 17 gold / 30 WGs
- 2021May: 16 gold / 30 WGs
- 2021Sep: 26 gold / 33 WGs
- 2022Jan: 29 gold / 33 WGs
- 2022May: 25 gold / 33 WGs
- 2022Sep: 26 gold / 33 WGs
- 2023Jan: 26 gold / 32 WGs
- 2023May: 24 gold / 32 WGs
- 2023Sep: 27 gold / 32 WGs
- 2024Jan: 25 gold / 32 WGs
- 2024May: 27 gold / 32 WGs
- 2024Sep: 24 gold / 32 WGs
- 2025Jan: 21 gold / 31 WGs
- 2025May: 21 gold / 31 WGs
- 2025Sep: 24 gold / 31 WGs
- 2026Jan: 21 gold / 31 WGs
- 2026May: 15 gold / 30 WGs
- 2026Sep: 25 gold / 30 WGs
