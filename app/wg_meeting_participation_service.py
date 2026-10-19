"""
Serve Confluence meeting-participation rollups for the dashboard UI.

Loads offline JSON produced by the minutes-participation ETL in
hl7-standards-dev-data and copied into data/standards-development/.
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_PATH = Path("data/standards-development/wg_meeting_participation.json")
DEFAULT_TRIMESTERS_PATH = Path(
    "data/standards-development/wg_meeting_participation_trimesters.json"
)
DEFAULT_MEETINGS_PATH = Path("data/standards-development/wg_meeting_meetings.json")
DEFAULT_PEOPLE_PATH = Path("data/standards-development/wg_meeting_people.json")
DEFAULT_ORGS_PATH = Path("data/standards-development/wg_meeting_organizations.json")
DEFAULT_STATUS_PATH = Path("data/standards-development/wg_status.json")


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(sum(values) / len(values))


class WgMeetingParticipationService:
    def __init__(
        self,
        summary_path: Optional[Path] = None,
        trimesters_path: Optional[Path] = None,
        meetings_path: Optional[Path] = None,
        people_path: Optional[Path] = None,
        orgs_path: Optional[Path] = None,
        status_path: Optional[Path] = None,
    ):
        self.summary_path = Path(summary_path) if summary_path else DEFAULT_SUMMARY_PATH
        self.trimesters_path = (
            Path(trimesters_path) if trimesters_path else DEFAULT_TRIMESTERS_PATH
        )
        self.meetings_path = Path(meetings_path) if meetings_path else DEFAULT_MEETINGS_PATH
        self.people_path = Path(people_path) if people_path else DEFAULT_PEOPLE_PATH
        self.orgs_path = Path(orgs_path) if orgs_path else DEFAULT_ORGS_PATH
        self.status_path = Path(status_path) if status_path else DEFAULT_STATUS_PATH
        self._cache: Dict[str, Any] = {}
        self._mtimes: Dict[str, float] = {}

    def _load_json(self, path: Path, cache_key: str) -> Dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(
                f"Meeting participation data not found at {path}. "
                "Copy JSON from the data repository minutes-participation outputs."
            )
        mtime = path.stat().st_mtime
        if cache_key in self._cache and self._mtimes.get(cache_key) == mtime:
            return self._cache[cache_key]
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        self._cache[cache_key] = payload
        self._mtimes[cache_key] = mtime
        return payload

    def _status_payload(self) -> Dict[str, Any]:
        if not self.status_path.is_file():
            return {}
        try:
            return self._load_json(self.status_path, "status")
        except (OSError, json.JSONDecodeError):
            return {}

    def _deprecated_keys(self) -> set:
        return set(self._status_payload().get("deprecated_keys") or [])

    def _deprecated_names_lower(self) -> set:
        status = self._status_payload()
        names = set(status.get("deprecated_names_lower") or [])
        for row in status.get("deprecated") or []:
            n = (row.get("wg_name") or "").strip().lower()
            if n:
                names.add(n)
        return names

    def _excluded_keys(self) -> set:
        """Affiliate / region groups hidden from this dashboard (wg_status.excluded_keys)."""
        return set(self._status_payload().get("excluded_keys") or [])

    def _is_sunset(self, wg_key: Optional[str], wg_name: Optional[str] = None) -> bool:
        """Match /wg-health-history: sunset by deprecated key or display name."""
        if wg_key and wg_key in self._deprecated_keys():
            return True
        name = (wg_name or "").strip().lower()
        if name and name in self._deprecated_names_lower():
            return True
        return False

    @staticmethod
    def _usable_person_name(person: Dict[str, Any]) -> bool:
        """Drop template/placeholder roster names like ``**`` or ``** or``."""
        raw = (person.get("display_name") or person.get("name_norm") or "").strip()
        if not raw:
            return False
        low = raw.lower()
        if low in {"*", "**", "***", "x", "xx", "n/a", "na", "tbd", "none", "name", "or"}:
            return False
        if re.fullmatch(r"[\*\s\|or\-]+", low):
            return False
        letters = re.sub(r"[^a-z]", "", low)
        return len(letters) >= 2

    def reload(self) -> None:
        self._cache.clear()
        self._mtimes.clear()

    def get_summary(self) -> Dict[str, Any]:
        data = self._load_json(self.summary_path, "summary")
        excluded = self._excluded_keys()
        workgroups = [
            w for w in (data.get("workgroups") or []) if w.get("wg_key") not in excluded
        ]
        for row in workgroups:
            row["is_sunset"] = self._is_sunset(row.get("wg_key"), row.get("wg_name"))

        mapped = [w for w in workgroups if w.get("space_key")]
        with_attendance = [
            w for w in mapped if w.get("meetings_with_attendance") not in (None, 0)
        ]
        # Portfolio KPIs: only WGs that have a non-null metric (never coerce null→0).
        median_headcounts = [
            w["median_headcount"]
            for w in mapped
            if w.get("median_headcount") is not None
        ]
        pct_ge_5 = [
            w["pct_meetings_ge_5"]
            for w in mapped
            if w.get("pct_meetings_ge_5") is not None
        ]
        pct_beyond = [
            w["pct_present_beyond_cochairs"]
            for w in mapped
            if w.get("pct_present_beyond_cochairs") is not None
        ]
        coverage = [
            w["coverage_score"] for w in mapped if w.get("coverage_score") is not None
        ]
        review = [w for w in mapped if w.get("needs_attendance_review")]
        review_sorted = sorted(
            review,
            key=lambda w: (
                -(w.get("attendance_gap_rate") or 0),
                -((w.get("meetings_empty_attendance") or 0) + (w.get("meetings_unparseable") or 0)),
                w.get("wg_name") or "",
            ),
        )
        empty_total = sum((w.get("meetings_empty_attendance") or 0) for w in mapped)
        unparseable_total = sum((w.get("meetings_unparseable") or 0) for w in mapped)

        portfolio = {
            "workgroups_total": len(workgroups),
            "workgroups_mapped": len(mapped),
            "workgroups_with_attendance": len(with_attendance),
            "median_of_median_headcount": _median(median_headcounts),
            "mean_pct_meetings_ge_5": _mean(pct_ge_5),
            "mean_pct_present_beyond_cochairs": _mean(pct_beyond),
            "mean_coverage_score": _mean(coverage),
            "wgs_reporting_median_headcount": len(median_headcounts),
            "wgs_reporting_pct_ge_5": len(pct_ge_5),
            "wgs_reporting_beyond_cochairs": len(pct_beyond),
            "wgs_reporting_coverage": len(coverage),
            "needs_attendance_review_count": len(review),
            "meetings_empty_attendance_total": empty_total,
            "meetings_unparseable_total": unparseable_total,
            "attendance_review_top": [
                {
                    "wg_key": w.get("wg_key"),
                    "wg_name": w.get("wg_name"),
                    "attendance_gap_rate": w.get("attendance_gap_rate"),
                    "meetings_empty_attendance": w.get("meetings_empty_attendance"),
                    "meetings_unparseable": w.get("meetings_unparseable"),
                    "coverage_score": w.get("coverage_score"),
                }
                for w in review_sorted[:12]
            ],
        }

        return {
            "meta": data.get("meta") or {},
            "portfolio": portfolio,
            "workgroups": workgroups,
        }

    def get_trimesters(self) -> Dict[str, Any]:
        data = self._load_json(self.trimesters_path, "trimesters")
        excluded = self._excluded_keys()
        rows = []
        for row in data.get("rows") or []:
            if row.get("wg_key") in excluded:
                continue
            enriched = dict(row)
            enriched["is_sunset"] = self._is_sunset(
                enriched.get("wg_key"), enriched.get("wg_name")
            )
            rows.append(enriched)
        return {
            "meta": data.get("meta") or {},
            "trimesters": data.get("trimesters") or [],
            "trimester_labels": data.get("trimester_labels") or [],
            "rows": rows,
        }

    def get_meetings(self, wg_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._load_json(self.meetings_path, "meetings")
        meetings = list(data.get("meetings") or [])
        if wg_key:
            meetings = [m for m in meetings if m.get("wg_key") == wg_key]
            meetings.sort(
                key=lambda m: (m.get("meeting_date") is None, m.get("meeting_date") or "")
            )
        return {
            "meta": data.get("meta") or {},
            "wg_key": wg_key,
            "meetings": meetings,
            "count": len(meetings),
        }

    def get_people(self, wg_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._load_json(self.people_path, "people")
        people = list(data.get("people") or [])
        if wg_key:
            people = [p for p in people if p.get("wg_key") == wg_key]
        people = [p for p in people if self._usable_person_name(p)]
        people.sort(
            key=lambda p: (-(p.get("meetings_present") or 0), p.get("display_name") or "")
        )
        return {
            "meta": data.get("meta") or {},
            "wg_key": wg_key,
            "people": people,
            "count": len(people),
        }

    def get_organizations(self, wg_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._load_json(self.orgs_path, "orgs")
        organizations = list(data.get("organizations") or [])
        if wg_key:
            organizations = [o for o in organizations if o.get("wg_key") == wg_key]
        organizations.sort(
            key=lambda o: (
                -(o.get("meetings_represented") or 0),
                o.get("display_name") or "",
            )
        )
        return {
            "meta": data.get("meta") or {},
            "wg_key": wg_key,
            "organizations": organizations,
            "count": len(organizations),
        }

    def get_workgroup(self, wg_key: str) -> Dict[str, Any]:
        summary = self.get_summary()
        row = next(
            (w for w in summary["workgroups"] if w.get("wg_key") == wg_key),
            None,
        )
        if row is None:
            raise KeyError(f"Unknown work group key: {wg_key}")
        return {
            "meta": summary.get("meta") or {},
            "workgroup": row,
            "meetings": self.get_meetings(wg_key).get("meetings") or [],
            "people": self.get_people(wg_key).get("people") or [],
            "organizations": self.get_organizations(wg_key).get("organizations") or [],
        }
