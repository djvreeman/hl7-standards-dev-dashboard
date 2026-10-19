"""
Parse HL7 WGM / Connectathon host countries from the New Attendees CSV
and map them onto dashboard T{N} periods.
"""
import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Meeting types that belong on the T{N} timeline. DevDays is skipped because it
# is not a trimester WGM and would collide with May (T2) when month-mapped.
MEETING_TYPE_PRIORITY = {
    "WGM": 3,
    "CONNECTATHON": 2,
}

# Calendar month → HL7 trimester. Matches the dashboard's T1/T2/T3 cadence:
# January WGM = T1, May WGM = T2, September WGM = T3.
MONTH_TO_TRIMESTER = {
    1: 1, 2: 1, 3: 1,
    4: 2, 5: 2, 6: 2,
    7: 3, 8: 3, 9: 3, 10: 3, 11: 3, 12: 3,
}

# Lowercase country / alias → ISO 3166-1 alpha-2. Virtual/Hybrid are special.
COUNTRY_ISO2 = {
    "usa": "us",
    "us": "us",
    "u.s.": "us",
    "u.s.a.": "us",
    "united states": "us",
    "united states of america": "us",
    "canada": "ca",
    "netherlands": "nl",
    "the netherlands": "nl",
    "holland": "nl",
    "spain": "es",
    "germany": "de",
    "france": "fr",
    "australia": "au",
    "japan": "jp",
    "brazil": "br",
    "united kingdom": "gb",
    "uk": "gb",
    "great britain": "gb",
    "england": "gb",
    "ireland": "ie",
    "italy": "it",
    "switzerland": "ch",
    "sweden": "se",
    "norway": "no",
    "denmark": "dk",
    "finland": "fi",
    "belgium": "be",
    "austria": "at",
    "portugal": "pt",
    "greece": "gr",
    "poland": "pl",
    "india": "in",
    "china": "cn",
    "south korea": "kr",
    "korea": "kr",
    "korea, rep.": "kr",
    "new zealand": "nz",
    "singapore": "sg",
    "taiwan": "tw",
    "hong kong": "hk",
    "mexico": "mx",
    "argentina": "ar",
    "chile": "cl",
    "south africa": "za",
    "israel": "il",
    "czech republic": "cz",
    "czechia": "cz",
    "estonia": "ee",
    "latvia": "lv",
    "lithuania": "lt",
    "romania": "ro",
    "hungary": "hu",
    "croatia": "hr",
    "slovenia": "si",
    "slovakia": "sk",
    "slovak republic": "sk",
}

DATE_RE = re.compile(r"^(\d{4})\D+(\d{1,2})$")


class MeetingLocationsService:
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = Path(csv_path) if csv_path else self._find_csv()
        self._data_cache: Optional[Dict[str, Dict[str, Any]]] = None

    @staticmethod
    def _find_csv() -> Path:
        candidates = [
            Path("data/raw/HL7 - New Attendees - All.csv"),
            Path("data/HL7 - New Attendees - All.csv"),
        ]
        for path in candidates:
            if path.exists():
                return path

        raw_dir = Path("data/raw")
        if raw_dir.exists():
            matches = sorted(raw_dir.glob("*New Attendees*.csv"))
            if matches:
                return matches[0]

        return candidates[0]

    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        if self._data_cache is not None:
            return self._data_cache

        locations: Dict[str, Dict[str, Any]] = {}
        if not self.csv_path.exists():
            logger.warning("Meeting locations CSV not found: %s", self.csv_path)
            self._data_cache = locations
            return locations

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                parsed = self._row_to_location(row)
                if not parsed:
                    continue
                period = parsed["period"]
                existing = locations.get(period)
                if existing is None or parsed["priority"] > existing["priority"]:
                    locations[period] = parsed

        for item in locations.values():
            item.pop("priority", None)

        self._data_cache = locations
        logger.info("Loaded %s meeting locations from %s", len(locations), self.csv_path)
        return locations

    def _row_to_location(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        date_str = (row.get("Date") or "").strip()
        country = (row.get("Country") or "").strip()
        if not date_str or not country:
            return None

        period = self._date_to_period(date_str)
        if not period:
            return None

        meeting_type = (row.get("Meeting Type") or "").strip()
        priority = MEETING_TYPE_PRIORITY.get(meeting_type.upper())
        if priority is None:
            return None

        kind, iso2 = self._classify_country(country)
        return {
            "period": period,
            "country": country,
            "iso2": iso2,
            "kind": kind,
            "meeting": (row.get("Orig Meeting") or "").strip(),
            "format": (row.get("Format") or "").strip(),
            "meeting_type": meeting_type,
            "priority": priority,
        }

    @staticmethod
    def _date_to_period(date_str: str) -> Optional[str]:
        match = DATE_RE.match(date_str.strip())
        if not match:
            return None
        year = int(match.group(1))
        month = int(match.group(2))
        if month < 1 or month > 12:
            return None
        trimester = MONTH_TO_TRIMESTER[month]
        return f"{year}-T{trimester}"

    @staticmethod
    def _classify_country(country: str) -> tuple:
        normalized = country.strip().lower()
        if normalized in {"virtual", "online", "remote"}:
            return "virtual", None
        if normalized in {"hybrid"}:
            return "hybrid", None
        iso2 = COUNTRY_ISO2.get(normalized)
        if iso2:
            return "country", iso2
        return "unknown", None

    def get_locations(self) -> Dict[str, Dict[str, Any]]:
        return self._load_data()

    def get_locations_payload(self) -> Dict[str, Any]:
        locations = self.get_locations()
        return {
            "source": str(self.csv_path),
            "count": len(locations),
            "locations": locations,
        }

    def refresh_data(self) -> None:
        self._data_cache = None
        self.csv_path = self._find_csv()
        self._load_data()
