#!/usr/bin/env python3
"""
Compute Indicator 16: Countries with national adoption of HL7 specifications.

KPI value = unique countries in:
  (State of FHIR Survey: regulation Mandates OR Advises FHIR)
  ∪
  (manually verified map countries from Zotero group tags)

Also emits review queues for survey drop-offs and survey-only countries
not yet verified on the map / Zotero library.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "national-adoption"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "national-adoption"

ZOTERO_GROUP_ID = 5872416
ZOTERO_API_BASE = f"https://api.zotero.org/groups/{ZOTERO_GROUP_ID}"
MAP_URL = "https://danielvreeman.com/hl7-map/"
DEFAULT_NOTE = (
    "Results for FHIR only: union of {survey_year} State of FHIR Survey "
    "(regulation mandates or advises FHIR) and manually verified national "
    f"evidence at {MAP_URL}."
)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def survey_countries(survey: dict[str, Any]) -> set[str]:
    return set(survey.get("mandated", [])) | set(survey.get("advised", []))


def load_survey(year: int) -> dict[str, Any]:
    path = RAW_DIR / f"survey_fhir_regulation_{year}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing survey extract {path}. Add mandated/advised country lists "
            "from that year's State of FHIR Survey report."
        )
    return load_json(path)


def load_non_country_tags() -> set[str]:
    path = RAW_DIR / "zotero_non_country_tags.json"
    data = load_json(path)
    return set(data.get("tags", []))


def fetch_zotero_tags(api_key: str | None = None) -> list[dict[str, Any]]:
    """Return all tags from the HL7 Standards Zotero group."""
    headers = {
        "Zotero-API-Version": "3",
        "User-Agent": "hl7-national-adoption-kpi/1.0",
    }
    if api_key:
        headers["Zotero-API-Key"] = api_key

    tags: list[dict[str, Any]] = []
    start = 0
    while True:
        url = f"{ZOTERO_API_BASE}/tags?limit=100&start={start}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Zotero API error {exc.code} for {url}. "
                "Public group reads usually work without a key; "
                "pass --zotero-api-key if the library becomes private."
            ) from exc
        if not batch:
            break
        tags.extend(batch)
        start += len(batch)
        if len(batch) < 100:
            break
    return tags


def map_countries_from_tags(
    tags: list[dict[str, Any]], non_country: set[str]
) -> dict[str, int]:
    """Country tag -> item count, excluding topical/regional tags."""
    countries: dict[str, int] = {}
    for entry in tags:
        name = entry.get("tag", "")
        if not name or name in non_country:
            continue
        countries[name] = int(entry.get("meta", {}).get("numItems", 0))
    return dict(sorted(countries.items()))


def load_manual_map_countries() -> dict[str, dict[str, Any]]:
    """Countries confirmed for the map ahead of / beside Zotero country tags."""
    path = RAW_DIR / "map_manual_countries.json"
    if not path.exists():
        return {}
    data = load_json(path)
    out: dict[str, dict[str, Any]] = {}
    for entry in data.get("countries", []):
        name = entry.get("country")
        if name:
            out[name] = entry
    return out


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute(
    survey_year: int,
    prior_survey_year: int | None,
    zotero_api_key: str | None,
) -> dict[str, Any]:
    survey = load_survey(survey_year)
    current = survey_countries(survey)
    non_country = load_non_country_tags()
    zotero_tags = fetch_zotero_tags(zotero_api_key)
    map_counts = map_countries_from_tags(zotero_tags, non_country)
    manual_map = load_manual_map_countries()
    # Manual confirmations count toward the map leg even before Zotero tags exist.
    for name in manual_map:
        map_counts.setdefault(name, 0)
    map_set = set(map_counts)

    union = sorted(current | map_set)
    both = sorted(current & map_set)
    survey_only = sorted(current - map_set)
    map_only = sorted(map_set - current)

    prior_payload: dict[str, Any] | None = None
    prior_set: set[str] = set()
    if prior_survey_year is not None:
        prior_payload = load_survey(prior_survey_year)
        prior_set = survey_countries(prior_payload)

    dropped_from_survey = sorted(prior_set - current)
    # Highest-priority review: previously surveyed positive, gone from current
    # survey, and not yet on the verified map.
    review_priority = sorted((prior_set - current) - map_set)
    # Still useful to re-check even if already on the map (stale evidence?).
    dropped_but_on_map = sorted((prior_set - current) & map_set)

    note = DEFAULT_NOTE.format(survey_year=survey_year)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indicator_id": 16,
        "indicator_name": "Countries with national adoption of HL7 specifications",
        "method": (
            "Union of State of FHIR Survey countries where regulation mandates "
            "or advises FHIR, and manually verified map countries (Zotero "
            f"group {ZOTERO_GROUP_ID} country tags / {MAP_URL})."
        ),
        "survey_year": survey_year,
        "prior_survey_year": prior_survey_year,
        "kpi_value": len(union),
        "kpi_notes": note,
        "counts": {
            "survey_mandated_or_advised": len(current),
            "map_verified": len(map_set),
            "union": len(union),
            "intersection": len(both),
            "survey_only": len(survey_only),
            "map_only": len(map_only),
            "dropped_from_prior_survey": len(dropped_from_survey),
            "review_priority_not_on_map": len(review_priority),
        },
        "countries": {
            "union": union,
            "survey": sorted(current),
            "map": sorted(map_set),
            "both": both,
            "survey_only": survey_only,
            "map_only": map_only,
            "dropped_from_prior_survey": dropped_from_survey,
            "review_priority_not_on_map": review_priority,
            "dropped_but_already_on_map": dropped_but_on_map,
        },
        "map_tag_item_counts": map_counts,
        "map_manual_countries": sorted(manual_map),
        "map_manual_details": manual_map,
        "survey_source": survey.get("source"),
        "prior_survey_source": prior_payload.get("source") if prior_payload else None,
        "zotero_group": ZOTERO_GROUP_ID,
        "map_url": MAP_URL,
    }
    return result


def print_summary(result: dict[str, Any]) -> None:
    counts = result["counts"]
    countries = result["countries"]
    print(f"Indicator 16 KPI value: {result['kpi_value']}")
    print(f"  Survey ({result['survey_year']}): {counts['survey_mandated_or_advised']}")
    print(f"  Map verified: {counts['map_verified']}")
    print(f"  Union: {counts['union']}")
    print(f"  Intersection: {counts['intersection']}")
    print()
    print("Map-only (survey missed this year):")
    for c in countries["map_only"]:
        print(f"  - {c}")
    print()
    print("Survey-only (not yet map/Zotero verified) — verification backlog:")
    for c in countries["survey_only"]:
        print(f"  - {c}")
    print()
    if result["prior_survey_year"] is not None:
        print(
            f"Dropped from {result['prior_survey_year']} survey "
            f"({counts['dropped_from_prior_survey']}):"
        )
        for c in countries["dropped_from_prior_survey"]:
            print(f"  - {c}")
        print()
        print(
            "PRIORITY manual review / Zotero candidates "
            "(prior survey positive, absent this year, not on map):"
        )
        if countries["review_priority_not_on_map"]:
            for c in countries["review_priority_not_on_map"]:
                print(f"  - {c}")
        else:
            print("  (none)")
        if countries["dropped_but_already_on_map"]:
            print()
            print("Dropped from survey but already on map:")
            for c in countries["dropped_but_already_on_map"]:
                print(f"  - {c}")
    print()
    print(f"Suggested Notes field:\n  {result['kpi_notes']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--survey-year",
        type=int,
        default=2026,
        help="Survey year JSON extract to use for the current period (default: 2026)",
    )
    parser.add_argument(
        "--prior-survey-year",
        type=int,
        default=2025,
        help="Prior survey year for drop-off detection (default: 2025; use 0 to skip)",
    )
    parser.add_argument(
        "--zotero-api-key",
        default=None,
        help="Optional Zotero API key (needed only if group library reading is restricted)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help=f"Directory for JSON/CSV outputs (default: {PROCESSED_DIR})",
    )
    args = parser.parse_args(argv)

    prior = None if args.prior_survey_year == 0 else args.prior_survey_year
    result = compute(args.survey_year, prior, args.zotero_api_key)

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{args.survey_year}"
    summary_path = out_dir / f"national_adoption_{stamp}.json"
    write_json(summary_path, result)

    review_rows = [
        {
            "country": c,
            "queue": "priority_prior_survey_dropoff_not_on_map",
            "action": "Focused manual review; add evidence to Zotero if confirmed",
        }
        for c in result["countries"]["review_priority_not_on_map"]
    ] + [
        {
            "country": c,
            "queue": "survey_only_not_on_map",
            "action": "Verify survey claim; add to Zotero/map when confirmed",
        }
        for c in result["countries"]["survey_only"]
    ]
    review_path = out_dir / f"national_adoption_review_queue_{stamp}.csv"
    write_csv(
        review_path,
        review_rows,
        ["country", "queue", "action"],
    )

    union_path = out_dir / f"national_adoption_union_{stamp}.csv"
    write_csv(
        union_path,
        [
            {
                "country": c,
                "in_survey": "Y" if c in result["countries"]["survey"] else "N",
                "in_map": "Y" if c in result["countries"]["map"] else "N",
            }
            for c in result["countries"]["union"]
        ],
        ["country", "in_survey", "in_map"],
    )

    print_summary(result)
    print()
    print(f"Wrote {summary_path}")
    print(f"Wrote {union_path}")
    print(f"Wrote {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
