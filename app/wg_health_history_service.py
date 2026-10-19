"""
Serve Final Work Group Health scorecard history for the dashboard UI.

Loads the one-off normalized JSON produced in the data repository
(scripts/workgroup-health/normalize-wgh-finals.py) and copied here.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = Path("data/standards-development/wg_health_finals.json")
DEFAULT_VALIDATION_PATH = Path("data/standards-development/wg_health_finals_validation.json")

# Final publication cycle → preceding HL7 trimester (the period the scorecard reports).
# Jan/Feb → prior-year T3; May → same-year T1; Sep → same-year T2. e.g. 2026Sep → 26T2
CONFLUENCE_PAGE_URL = "https://confluence.hl7.org/pages/viewpage.action?pageId={page_id}"
CONFLUENCE_ATTACHMENT_URL = (
    "https://confluence.hl7.org/download/attachments/{page_id}/{filename}?api=v2"
)


def cycle_to_tn_label(cycle: Optional[str]) -> str:
    if not cycle:
        return ""
    match = re.match(r"(20\d{2})(Jan|Feb|May|Sep)$", cycle)
    if not match:
        return cycle
    year = int(match.group(1))
    month = match.group(2)
    if month in ("Jan", "Feb"):
        return f"{(year - 1) % 100:02d}T3"
    if month == "May":
        return f"{year % 100:02d}T1"
    return f"{year % 100:02d}T2"


def cycle_display_label(cycle_row: Optional[Dict[str, Any]]) -> str:
    """Prefer ETL period_label; fall back to publication-cycle mapping."""
    if not cycle_row:
        return ""
    return cycle_row.get("period_label") or cycle_to_tn_label(cycle_row.get("cycle"))


def confluence_page_url(page_id: Optional[str]) -> Optional[str]:
    if not page_id:
        return None
    return CONFLUENCE_PAGE_URL.format(page_id=page_id)


def confluence_attachment_url(page_id: Optional[str], filename: Optional[str]) -> Optional[str]:
    if not page_id or not filename:
        return None
    from urllib.parse import quote

    return CONFLUENCE_ATTACHMENT_URL.format(
        page_id=page_id,
        filename=quote(filename, safe="."),
    )


class WgHealthHistoryService:
    def __init__(
        self,
        data_path: Optional[Path] = None,
        validation_path: Optional[Path] = None,
    ):
        self.data_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        self.validation_path = Path(validation_path) if validation_path else DEFAULT_VALIDATION_PATH
        self._payload: Optional[Dict[str, Any]] = None
        self._payload_mtime: Optional[float] = None
        self._validation: Optional[Dict[str, Any]] = None
        self._validation_mtime: Optional[float] = None

    def _load(self) -> Dict[str, Any]:
        if not self.data_path.is_file():
            raise FileNotFoundError(
                f"WG Health finals data not found at {self.data_path}. "
                "Copy wg_health_finals.json from the data repository."
            )
        mtime = self.data_path.stat().st_mtime
        if self._payload is not None and self._payload_mtime == mtime:
            return self._payload
        with self.data_path.open(encoding="utf-8") as fh:
            self._payload = json.load(fh)
        self._payload_mtime = mtime
        return self._payload

    def _load_validation(self) -> Optional[Dict[str, Any]]:
        if not self.validation_path.is_file():
            return None
        mtime = self.validation_path.stat().st_mtime
        if self._validation is not None and self._validation_mtime == mtime:
            return self._validation
        with self.validation_path.open(encoding="utf-8") as fh:
            self._validation = json.load(fh)
        self._validation_mtime = mtime
        return self._validation

    def reload(self) -> Dict[str, Any]:
        self._payload = None
        self._payload_mtime = None
        self._validation = None
        self._validation_mtime = None
        return self._load()

    def get_overview(self) -> Dict[str, Any]:
        data = self._load()
        cycles = data.get("cycles") or []
        workgroups = self._workgroup_index(cycles)
        heatmap = self._build_heatmap(cycles, workgroups)
        latest = cycles[-1] if cycles else None
        gold_timeline = [
            {
                "cycle": c.get("cycle"),
                "label": cycle_display_label(c),
                "wg_count": len(c.get("workgroups") or []),
                "gold_star_count": c.get("gold_star_count")
                if c.get("gold_star_count") is not None
                else sum(1 for w in (c.get("workgroups") or []) if w.get("gold_star")),
            }
            for c in cycles
        ]
        latest_gold = gold_timeline[-1]["gold_star_count"] if gold_timeline else 0
        return {
            "meta": data.get("meta") or {},
            "validation": self._validation_summary(),
            "cycles": [
                {
                    "cycle": c.get("cycle"),
                    "label": cycle_display_label(c),
                    "period_label": c.get("period_label") or cycle_to_tn_label(c.get("cycle")),
                    "page_id": c.get("page_id"),
                    "confluence_url": confluence_page_url(c.get("page_id")),
                    "wg_count": len(c.get("workgroups") or []),
                    "gold_star_count": next(
                        (g["gold_star_count"] for g in gold_timeline if g["cycle"] == c.get("cycle")),
                        0,
                    ),
                    "source_files": [
                        {
                            "filename": s.get("filename"),
                            "steering_division": s.get("steering_division"),
                            "wg_count": s.get("wg_count"),
                            "confluence_url": confluence_attachment_url(
                                c.get("page_id"), s.get("filename")
                            ),
                        }
                        for s in (c.get("source_files") or [])
                    ],
                }
                for c in cycles
            ],
            "workgroups": workgroups,
            "heatmap": heatmap,
            "gold_star_timeline": gold_timeline,
            "latest_cycle": latest.get("cycle") if latest else None,
            "summary": {
                "cycle_count": len(cycles),
                "workgroup_count": len(workgroups),
                "latest_cycle": latest.get("cycle") if latest else None,
                "latest_cycle_label": cycle_display_label(latest) if latest else None,
                "latest_wg_count": len(latest.get("workgroups") or []) if latest else 0,
                "latest_gold_star_count": latest_gold,
            },
        }

    def get_validation(self) -> Dict[str, Any]:
        report = self._load_validation()
        if not report:
            raise FileNotFoundError(
                f"Validation report not found at {self.validation_path}. "
                "Run validate-wgh-finals.py in the data repository."
            )
        return report

    def get_cycle(self, cycle: str) -> Dict[str, Any]:
        data = self._load()
        match = next((c for c in data.get("cycles") or [] if c.get("cycle") == cycle), None)
        if not match:
            raise KeyError(f"Cycle not found: {cycle}")
        workgroups = sorted(
            match.get("workgroups") or [],
            key=lambda w: (
                0 if w.get("gold_star") else 1,
                (w.get("wg_name") or "").lower(),
                w.get("wg_key") or "",
            ),
        )
        band_counts: Dict[str, int] = {}
        gold_count = 0
        for wg in workgroups:
            band = wg.get("health_band") or "present"
            band_counts[band] = band_counts.get(band, 0) + 1
            if wg.get("gold_star"):
                gold_count += 1
        page_id = match.get("page_id")
        source_files = []
        for s in match.get("source_files") or []:
            source_files.append(
                {
                    **s,
                    "confluence_url": confluence_attachment_url(page_id, s.get("filename")),
                }
            )
        return {
            "cycle": match.get("cycle"),
            "label": cycle_display_label(match),
            "period_label": match.get("period_label") or cycle_to_tn_label(match.get("cycle")),
            "page_id": page_id,
            "confluence_url": confluence_page_url(page_id),
            "metric_columns": match.get("metric_columns") or [],
            "source_files": source_files,
            "workgroups": workgroups,
            "band_counts": band_counts,
            "gold_star_count": match.get("gold_star_count", gold_count),
        }

    def get_workgroup(self, wg_key: str) -> Dict[str, Any]:
        data = self._load()
        cycles = data.get("cycles") or []
        display_name = None
        history: List[Dict[str, Any]] = []
        for cycle in cycles:
            row = next(
                (w for w in (cycle.get("workgroups") or []) if w.get("wg_key") == wg_key),
                None,
            )
            if row is None:
                history.append(
                    {
                        "cycle": cycle.get("cycle"),
                        "present": False,
                        "total_infractions": None,
                        "health_band": "absent",
                        "gold_star": False,
                        "prior_period_infractions": [],
                        "cells": {},
                        "steering_division": None,
                        "wg_name": None,
                    }
                )
                continue
            display_name = row.get("wg_name") or display_name
            history.append(
                {
                    "cycle": cycle.get("cycle"),
                    "present": True,
                    "total_infractions": row.get("total_infractions"),
                    "health_band": row.get("health_band"),
                    "gold_star": bool(row.get("gold_star")),
                    "prior_period_infractions": row.get("prior_period_infractions") or [],
                    "cells": row.get("cells") or {},
                    "steering_division": row.get("steering_division"),
                    "wg_name": row.get("wg_name"),
                    "metric_columns": cycle.get("metric_columns") or [],
                }
            )
        if display_name is None and not any(h.get("present") for h in history):
            raise KeyError(f"Work group not found: {wg_key}")
        # Newest Final first for drill-down tables
        history = list(reversed(history))
        present_history = [h for h in history if h.get("present")]
        gold_count = sum(1 for h in present_history if h.get("gold_star"))
        return {
            "wg_key": wg_key,
            "wg_name": display_name or wg_key,
            "history": history,
            "present_cycle_count": len(present_history),
            "gold_star_count": gold_count,
            "cycle_count": len(cycles),
        }

    def _validation_summary(self) -> Optional[Dict[str, Any]]:
        report = self._load_validation()
        if not report:
            return None
        return {
            "status": report.get("status"),
            "generated_at": report.get("generated_at"),
            "summary": report.get("summary"),
            "checks": report.get("checks"),
        }

    def _workgroup_index(self, cycles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        names: Dict[str, str] = {}
        first_seen: Dict[str, str] = {}
        last_seen: Dict[str, str] = {}
        gold_totals: Dict[str, int] = {}
        for cycle in cycles:
            cycle_id = cycle.get("cycle")
            for wg in cycle.get("workgroups") or []:
                key = wg.get("wg_key")
                if not key:
                    continue
                names[key] = wg.get("wg_name") or names.get(key) or key
                if key not in first_seen:
                    first_seen[key] = cycle_id
                last_seen[key] = cycle_id
                if wg.get("gold_star"):
                    gold_totals[key] = gold_totals.get(key, 0) + 1
        return [
            {
                "wg_key": key,
                "wg_name": names[key],
                "first_cycle": first_seen[key],
                "last_cycle": last_seen[key],
                "gold_star_count": gold_totals.get(key, 0),
            }
            for key in sorted(names.keys(), key=lambda k: names[k].lower())
        ]

    def _build_heatmap(
        self,
        cycles: List[Dict[str, Any]],
        workgroups: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        cycle_ids = [c.get("cycle") for c in cycles]
        lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for cycle in cycles:
            cycle_id = cycle.get("cycle")
            for wg in cycle.get("workgroups") or []:
                key = wg.get("wg_key")
                if not key:
                    continue
                lookup.setdefault(key, {})[cycle_id] = {
                    "total_infractions": wg.get("total_infractions"),
                    "health_band": wg.get("health_band") or "present",
                    "gold_star": bool(wg.get("gold_star")),
                }

        rows: List[Dict[str, Any]] = []
        for wg in workgroups:
            key = wg["wg_key"]
            cells = []
            for cycle_id in cycle_ids:
                cell = lookup.get(key, {}).get(cycle_id)
                if cell is None:
                    cells.append(
                        {
                            "cycle": cycle_id,
                            "total_infractions": None,
                            "health_band": "absent",
                            "gold_star": False,
                        }
                    )
                else:
                    cells.append(
                        {
                            "cycle": cycle_id,
                            "total_infractions": cell.get("total_infractions"),
                            "health_band": cell.get("health_band"),
                            "gold_star": cell.get("gold_star"),
                        }
                    )
            rows.append(
                {
                    "wg_key": key,
                    "wg_name": wg["wg_name"],
                    "cells": cells,
                }
            )
        return {
            "cycles": cycle_ids,
            "rows": rows,
        }
