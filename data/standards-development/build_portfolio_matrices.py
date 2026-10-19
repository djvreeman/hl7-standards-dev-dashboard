#!/usr/bin/env python3
"""
Rebuild FHIR resource-ownership and WG ballot-specs matrices for the dashboard.

Prerequisites:
  - FHIR core packages under tmp-fhir-packages/{r4,r4b,r5} (from packages.fhir.org)
  - Optional local FHIR checkout for "Current" (FHIR_SRC env or ../../fhir/source)
  - Ballot detail CSV (BALLOT_DETAIL env or sibling data-repo path below)

Usage (from dashboard repo root):
  python3 data/standards-development/build_portfolio_matrices.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASHBOARD_ROOT = HERE.parent.parent
OUT_DIR = HERE
PKG_DIR = HERE / "tmp-fhir-packages"
DEFAULT_FHIR_SRC = DASHBOARD_ROOT.parent / "fhir" / "source"
DEFAULT_BALLOT_CSV = (
    DASHBOARD_ROOT.parent
    / "hl7-standards-dev-data"
    / "data"
    / "working"
    / "process-documents"
    / "workgroup-health"
    / "wg-ballot-specs-detail.csv"
)
WG_EXT = "http://hl7.org/fhir/StructureDefinition/structuredefinition-wg"
EXCLUDED_TRIMESTERS_BEFORE = "2018T1"

# FHIR structuredefinition-wg codes (and close Jira keys) → WGH master key.
# Maintained crosswalk: do not invent display names from the raw code.
FHIR_WG_CODE_TO_KEY = {
    "brr": "biomedical-research-regulation",
    "cds": "clinical-decision-support",
    "cg": "clinical-genomics",
    "cqi": "clinical-quality-information",
    "cbcc": "community-based-care-and-privacy",
    "dev": "devices",
    "devices": "devices",  # newer FHIR tip code (alongside legacy "dev")
    "fhir": "fhir-infrastructure",  # legacy ownership code in FHIR core
    "fhir-i": "fhir-infrastructure",
    "fm": "financial-management",
    "ii": "imaging-integration",
    "inm": "infrastructure-and-messaging",
    "oo": "orders-and-observations",
    "pa": "patient-administration",
    "pc": "patient-care",
    "phx": "pharmacy",  # legacy Pharmacy code in FHIR core
    "pharm": "pharmacy",
    "pher": "public-health",
    "sec": "security",  # legacy Security code
    "security": "security",
    "sd": "structured-documents",
    "vocab": "terminology-infrastructure",
}

# Same preferred display names as normalize-wgh-finals.WG_DISPLAY
WG_DISPLAY = {
    "arden-syntax": "Arden Syntax",
    "biomedical-research-regulation": "Biomedical Research & Regulation",
    "clinical-decision-support": "Clinical Decision Support",
    "clinical-genomics": "Clinical Genomics",
    "clinical-information-modeling-initiative": "Clinical Information Modeling Initiative",
    "clinical-interoperability-council": "Clinical Interoperability Council",
    "clinical-quality-information": "Clinical Quality Information",
    "community-based-care-and-privacy": "Community-Based Care and Privacy",
    "conformance": "Conformance",
    "cross-group-projects": "Cross-Group Projects",
    "devices": "Devices",
    "electronic-health-records": "Electronic Health Records",
    "emergency-care": "Emergency Care",
    "fhir-infrastructure": "FHIR Infrastructure",
    "financial-management": "Financial Management",
    "human-and-social-services": "Human and Social Services",
    "imaging-integration": "Imaging Integration",
    "implementable-technology-specifications": "Implementable Technology Specifications",
    "infrastructure-and-messaging": "Infrastructure and Messaging",
    "learning-health-systems": "Learning Health Systems",
    "mobile-health": "Mobile Health",
    "orchestration-services-architecture": "Orchestration, Services, and Architecture",
    "orders-and-observations": "Orders & Observations",
    "patient-administration": "Patient Administration",
    "patient-care": "Patient Care",
    "patient-empowerment": "Patient Empowerment",
    "payer-provider-information-exchange": "Payer/Provider Information Exchange",
    "pharmacy": "Pharmacy",
    "public-health": "Public Health",
    "security": "Security",
    "structured-documents": "Structured Documents",
    "terminology-infrastructure": "Terminology Infrastructure",
}

BALLOT_NAME_TO_KEY = {
    "arden syntax": "arden-syntax",
    "biomedical research & regulation": "biomedical-research-regulation",
    "cimi": "clinical-information-modeling-initiative",
    "clinical decision support": "clinical-decision-support",
    "clinical genomics": "clinical-genomics",
    "clinical information modeling initiative": "clinical-information-modeling-initiative",
    "clinical interoperability council": "clinical-interoperability-council",
    "clinical quality information": "clinical-quality-information",
    "community-based care and privacy": "community-based-care-and-privacy",
    "conformance": "conformance",
    "cross-group projects": "cross-group-projects",
    "devices": "devices",
    "electronic health record": "electronic-health-records",
    "electronic health records": "electronic-health-records",
    "emergency care": "emergency-care",
    "fhir infrastructure": "fhir-infrastructure",
    "financial management": "financial-management",
    "financial mgmt": "financial-management",
    "human and social services": "human-and-social-services",
    "imaging integration": "imaging-integration",
    "implementable technology specifications": "implementable-technology-specifications",
    "infrastructure & messaging": "infrastructure-and-messaging",
    "infrastructure and messaging": "infrastructure-and-messaging",
    "learning health systems": "learning-health-systems",
    "mobile health": "mobile-health",
    "orchestration, services, and architecture": "orchestration-services-architecture",
    "orders & observations": "orders-and-observations",
    "orders and observations": "orders-and-observations",
    "patient administration": "patient-administration",
    "patient care": "patient-care",
    "patient empowerment": "patient-empowerment",
    "payer/provider information exchange": "payer-provider-information-exchange",
    "pharmacy": "pharmacy",
    "public health": "public-health",
    "security": "security",
    "structured documents": "structured-documents",
    "terminology infrastructure": "terminology-infrastructure",
}


def extract_from_json_sd(obj):
    if obj.get("resourceType") != "StructureDefinition":
        return None
    if obj.get("kind") != "resource":
        return None
    derivation = obj.get("derivation")
    if derivation and derivation != "specialization":
        return None
    rtype = obj.get("type") or obj.get("name") or obj.get("id")
    if not rtype:
        return None
    wg = None
    for ext in obj.get("extension") or []:
        if ext.get("url") == WG_EXT:
            wg = ext.get("valueCode")
            break
    if not wg:
        return None
    return rtype, wg


def extract_from_package(pkg_path: Path):
    counts: Counter = Counter()
    resources = []
    for p in pkg_path.rglob("StructureDefinition-*.json"):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = []
        if obj.get("resourceType") == "Bundle":
            for e in obj.get("entry") or []:
                if e.get("resource"):
                    items.append(e["resource"])
        else:
            items.append(obj)
        for it in items:
            hit = extract_from_json_sd(it)
            if hit:
                rtype, wg = hit
                counts[wg] += 1
                resources.append({"resource": rtype, "wg_key": wg})
    return counts, resources


def extract_from_xml_tree(src: Path):
    counts: Counter = Counter()
    resources = []
    wg_re = re.compile(
        r'url=["\']http://hl7\.org/fhir/StructureDefinition/structuredefinition-wg["\']'
        r'[\s\S]*?<valueCode value=["\']([^"\']+)["\']',
        re.I,
    )
    for p in src.rglob("structuredefinition-*.xml"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r'<kind\s+value=["\']resource["\']', text):
            continue
        if re.search(r'<derivation\s+value=["\']constraint["\']', text):
            continue
        m = wg_re.search(text)
        if not m:
            continue
        tm = re.search(r'<type\s+value=["\']([^"\']+)["\']', text)
        rtype = tm.group(1) if tm else p.stem.replace("structuredefinition-", "")
        wg = m.group(1)
        counts[wg] += 1
        resources.append({"resource": rtype, "wg_key": wg})
    return counts, resources


def short_tri(t: str) -> str:
    m = re.match(r"(\d{4})T([123])", t)
    if m:
        return f"{m.group(1)[2:]}T{m.group(2)}"
    return t


def build_fhir() -> dict:
    fhir_src = Path(os.environ.get("FHIR_SRC", DEFAULT_FHIR_SRC))
    versions = []
    # Accumulate by master WG key after remapping FHIR codes
    merged: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    extractors = [
        ("R4", PKG_DIR / "r4", lambda: extract_from_package(PKG_DIR / "r4")),
        ("R4B", PKG_DIR / "r4b", lambda: extract_from_package(PKG_DIR / "r4b")),
        ("R5", PKG_DIR / "r5", lambda: extract_from_package(PKG_DIR / "r5")),
    ]
    if fhir_src.is_dir():
        extractors.append(("Current", fhir_src, lambda: extract_from_xml_tree(fhir_src)))
    else:
        print(f"Skipping Current — FHIR source not found at {fhir_src}", file=sys.stderr)

    for label, path, extractor in extractors:
        if label != "Current" and not path.is_dir():
            raise FileNotFoundError(
                f"Missing package extract at {path}. Download hl7.fhir.*.core into tmp-fhir-packages/."
            )
        print(f"Extracting {label}…")
        counts, _resources = extractor()
        print(f"  {sum(counts.values())} resources, {len(counts)} raw WG codes")
        for code, n in counts.items():
            key = FHIR_WG_CODE_TO_KEY.get(code)
            if not key:
                print(f"  WARNING: unmapped structuredefinition-wg code {code!r}", file=sys.stderr)
                key = code
            merged[key][label] += n
        versions.append(label)

    rows = []
    for wg_key in sorted(merged.keys(), key=lambda k: WG_DISPLAY.get(k, k).lower()):
        cells = []
        for v in versions:
            n = merged[wg_key].get(v, 0)
            cells.append({"version": v, "count": n if n else None})
        if any(c["count"] for c in cells):
            rows.append(
                {
                    "wg_key": wg_key,
                    "wg_name": WG_DISPLAY.get(wg_key, wg_key),
                    "cells": cells,
                    "total": sum(merged[wg_key].values()),
                }
            )

    sources = {
        "R4": "hl7.fhir.r4.core@4.0.1 (packages.fhir.org)",
        "R4B": "hl7.fhir.r4b.core@4.3.0 (packages.fhir.org)",
        "R5": "hl7.fhir.r5.core@5.0.0 (packages.fhir.org)",
    }
    if "Current" in versions:
        sources["Current"] = "local FHIR core checkout tip (post-R5 / R6 draft)"

    version_totals = {
        v: sum(merged[k].get(v, 0) for k in merged) for v in versions
    }

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": (
                "Count of FHIR base resources owned by each work group "
                "(structuredefinition-wg) per FHIR core version."
            ),
            "sources": sources,
            "method": (
                "StructureDefinition kind=resource, derivation≠constraint, "
                "extension structuredefinition-wg; codes remapped to WGH master keys"
            ),
            "work_group_master": (
                "Display names and keys from WGH master data (normalize-wgh-finals WG_DISPLAY). "
                "FHIR structuredefinition-wg codes remapped via FHIR_WG_CODE_TO_KEY "
                "(fhir→fhir-infrastructure, phx→pharmacy, sec→security, …)."
            ),
        },
        "versions": versions,
        "version_totals": version_totals,
        "rows": rows,
    }


def build_ballot() -> dict:
    ballot_csv = Path(os.environ.get("BALLOT_DETAIL", DEFAULT_BALLOT_CSV))
    if not ballot_csv.is_file():
        raise FileNotFoundError(f"Ballot detail CSV not found: {ballot_csv}")

    shutil.copy2(ballot_csv, OUT_DIR / "wg_ballot_specs_detail.csv")
    detail_rows = list(csv.DictReader(ballot_csv.open(encoding="utf-8")))

    by_wg_t: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    by_wg_t_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    trimesters: set[str] = set()
    for r in detail_rows:
        raw_name = (r.get("work_group") or "").strip()
        tri = (r.get("trimester") or "").strip()
        spec = (r.get("specification") or "").strip()
        if not raw_name or not tri or not spec or raw_name == "Unmatched":
            continue
        if tri < EXCLUDED_TRIMESTERS_BEFORE:
            continue
        key = BALLOT_NAME_TO_KEY.get(raw_name.lower())
        if not key:
            print(f"  WARNING: unmapped ballot WG name {raw_name!r}", file=sys.stderr)
            key = raw_name.lower().replace(" ", "-").replace("&", "and")
            WG_DISPLAY.setdefault(key, raw_name)
        by_wg_t[key][tri].add(spec)
        by_wg_t_events[key][tri] += 1
        trimesters.add(tri)

    tri_cols = sorted(trimesters)
    ballot_rows = []
    for wg_key in sorted(by_wg_t.keys(), key=lambda k: WG_DISPLAY.get(k, k).lower()):
        cells = []
        for t in tri_cols:
            n = len(by_wg_t[wg_key][t])
            cells.append(
                {
                    "trimester": t,
                    "label": short_tri(t),
                    "count": n if n else None,
                    "events": by_wg_t_events[wg_key][t] or None,
                }
            )
        ballot_rows.append(
            {
                "wg_key": wg_key,
                "wg_name": WG_DISPLAY.get(wg_key, wg_key),
                "cells": cells,
                "total_specs_events": sum(by_wg_t_events[wg_key].values()),
                "total_unique_specs": len(set().union(*by_wg_t[wg_key].values()))
                if by_wg_t[wg_key]
                else 0,
            }
        )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "description": (
                "Number of distinct specifications balloted by each work group "
                "per HL7 trimester. Sponsorship via SPECS.json defaultWorkgroup."
            ),
            "source_file": "wg_ballot_specs_detail.csv",
            "count_unit": "unique specifications per trimester",
            "trimester_rule": "T1 Jan–Apr, T2 May–Aug, T3 Sep–Dec",
            "coverage_from": EXCLUDED_TRIMESTERS_BEFORE,
            "work_group_master": (
                "Display names and keys from WGH master data (normalize-wgh-finals WG_DISPLAY)."
            ),
        },
        "trimesters": tri_cols,
        "trimester_labels": [short_tri(t) for t in tri_cols],
        "trimester_totals": {
            t: len(set().union(*(by_wg_t[wg][t] for wg in by_wg_t))) for t in tri_cols
        },
        "rows": ballot_rows,
    }


def main() -> int:
    fhir = build_fhir()
    ballot = build_ballot()

    fhir_out = OUT_DIR / "fhir_resource_ownership_matrix.json"
    ballot_out = OUT_DIR / "wg_ballot_specs_matrix.json"
    fhir_out.write_text(json.dumps(fhir, indent=2), encoding="utf-8")
    ballot_out.write_text(json.dumps(ballot, indent=2), encoding="utf-8")
    print(f"Wrote {fhir_out} ({len(fhir['rows'])} WGs)")
    print(f"Wrote {ballot_out} ({len(ballot['rows'])} WGs, {len(ballot['trimesters'])} trimesters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
