"""Build paste-ready LLM prompts for the Standards Development dashboards."""
import base64
import binascii
import csv
import html
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from app.data_service import DataService
from app.meeting_locations_service import MeetingLocationsService
from app.models import KPIIndicator
from app.published_standards_service import PublishedStandardsService

STEWARD = "Standards Development"
INSIGHTS_SECTIONS = (
    ("Issues", "ISSUES"),
    ("Ballots", "BALLOTS"),
    ("Ecosystem", "ECOSYSTEM"),
)
PACKAGE_VERSIONS_NEW = ("49", "50", "51")
PACKAGE_VERSIONS_TOTAL = ("52", "53", "54")
PACKAGE_VERSION_IDS = PACKAGE_VERSIONS_NEW + PACKAGE_VERSIONS_TOTAL
PUBLISHED_SPEC_IDS = ("27", "47", "48")
SCOPES = ("cards", "insights")

CONTEXT_PATH = Path("data/standards-development/llm_context.md")
DEFINITIONS_PATH = Path("data/raw/indicator-definitions.csv")
PROMPT_DIR = Path("data/processed")
IMAGE_DIR = Path("static/indicators")

_TAG_RE = re.compile(r"<[^>]+>")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_WHITESPACE_RE = re.compile(r"\s+")


class PromptChartImage(BaseModel):
    filename: str
    title: str = ""
    data: str = Field(..., description="PNG bytes, base64-encoded")


class StandardsDevelopmentPromptRequest(BaseModel):
    scope: str = Field(..., description="cards or insights")
    question: str = ""
    kpi_only: bool = False
    include_publications: bool = False
    charts: List[PromptChartImage] = Field(default_factory=list)


class StandardsDevelopmentPromptService:
    def __init__(
        self,
        data_service: DataService,
        meeting_locations_service: MeetingLocationsService,
        published_standards_service: PublishedStandardsService,
        context_path: Path = CONTEXT_PATH,
        definitions_path: Path = DEFINITIONS_PATH,
    ):
        self.data_service = data_service
        self.meeting_locations_service = meeting_locations_service
        self.published_standards_service = published_standards_service
        self.context_path = context_path
        self.definitions_path = definitions_path

    def generate(
        self,
        scope: str,
        question: str = "",
        kpi_only: bool = False,
        include_publications: bool = False,
        charts: Optional[Sequence[Any]] = None,
    ) -> Dict[str, Any]:
        if scope not in SCOPES:
            raise ValueError("scope must be 'cards' or 'insights'")

        context = self._read_context()
        definitions = self._load_definitions()
        included: List[KPIIndicator] = []
        sections: List[str] = [
            context.rstrip(),
            "",
            "---",
            "",
            "# Data in this prompt",
            "",
            self._scope_intro(scope, kpi_only, include_publications),
            "",
        ]

        if scope == "cards":
            sections.extend(self._cards_sections(kpi_only, definitions, included))
        else:
            sections.extend(
                self._insights_sections(
                    kpi_only, include_publications, definitions, included
                )
            )

        if scope == "insights":
            attachments = self._chart_attachments(charts or [])
            image_kind = "charts"
        else:
            attachments = self._attachments(included)
            image_kind = "screenshots"
        sections.extend(self._attachment_lines(attachments, kind=image_kind))
        sections.extend(self._question_lines(question))

        prompt_text = "\n".join(sections).rstrip() + "\n"
        PROMPT_DIR.mkdir(parents=True, exist_ok=True)
        prompt_file = PROMPT_DIR / f"standards_development_llm_prompt_{scope}.txt"
        prompt_file.write_text(prompt_text, encoding="utf-8")
        package_file = self._write_package(scope, prompt_text, attachments)
        image_count = sum(1 for item in attachments if item.get("included"))

        return {
            "status": "success",
            "scope": scope,
            "prompt": prompt_text,
            "prompt_file": str(prompt_file),
            "package_file": str(package_file),
            "download_url": f"/api/standards-development/llm-prompt/{scope}/download",
            "attachments": [
                {key: value for key, value in item.items() if key != "bytes"}
                for item in attachments
            ],
            "image_count": image_count,
            "image_kind": image_kind if image_count else "none",
            "message": "LLM prompt created",
        }

    def _read_context(self) -> str:
        if not self.context_path.exists():
            raise FileNotFoundError(f"Context file not found: {self.context_path}")
        return self.context_path.read_text(encoding="utf-8")

    def _load_definitions(self) -> Dict[str, List[str]]:
        definitions: Dict[str, List[str]] = defaultdict(list)
        if not self.definitions_path.exists():
            return definitions
        with self.definitions_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                indicator_id = (row.get("ID") or "").strip()
                definition = (row.get("Definition") or "").strip()
                if indicator_id and definition:
                    definitions[indicator_id].append(definition)
        return definitions

    def _scope_intro(self, scope: str, kpi_only: bool, include_publications: bool) -> str:
        metadata = self.data_service.get_metadata()
        last_updated = metadata.last_updated if metadata else "unknown"
        generated = datetime.now().strftime("%Y-%m-%d")
        if scope == "cards":
            page = "Standards Development indicator cards"
            detail = (
                "Every indicator whose steward includes Standards Development, "
                "including uptime, participation, and citation cards that are not on the insights charts."
            )
        else:
            page = "Standards Development Insights"
            detail = (
                "Issues, Ballots, and Ecosystem charts, the R4/R4B/R5 package-version "
                "composites, the published-specifications chart, Working Group Meeting locations, "
                "and a publication summary."
            )
        kpi_line = "Show KPIs Only is on." if kpi_only else "Show KPIs Only is off."
        lines = [
            f"Source page: {page}.",
            detail,
            kpi_line,
            f"Indicator data last updated: {last_updated}.",
            f"Prompt generated: {generated}.",
        ]
        if scope == "insights":
            if include_publications:
                lines.append("Publication titles are included for every year.")
            else:
                lines.append("Publication titles are included for the latest year only.")
        return "\n".join(lines)

    def _cards_sections(
        self,
        kpi_only: bool,
        definitions: Dict[str, List[str]],
        included: List[KPIIndicator],
    ) -> List[str]:
        indicators = self._cards_indicators(kpi_only)
        included.extend(indicators)
        lines = ["## Indicator cards", ""]
        if not indicators:
            lines.append("No indicators match this page and filter.")
            lines.append("")
            return lines

        current_domain = None
        for indicator in indicators:
            if indicator.domain != current_domain:
                current_domain = indicator.domain
                lines.append(f"### {current_domain}")
                lines.append("")
            lines.extend(self._indicator_block(indicator, definitions, heading_level=4))
        return lines

    def _cards_indicators(self, kpi_only: bool) -> List[KPIIndicator]:
        data = self.data_service.get_kpi_data()
        if not data:
            return []
        indicators = [
            indicator
            for indicator in data.indicators.values()
            if STEWARD in indicator.stewards
        ]
        if kpi_only:
            indicators = [indicator for indicator in indicators if self._is_kpi(indicator)]
        indicators.sort(key=lambda indicator: (indicator.domain, indicator.name.lower()))
        return indicators

    def _insights_sections(
        self,
        kpi_only: bool,
        include_publications: bool,
        definitions: Dict[str, List[str]],
        included: List[KPIIndicator],
    ) -> List[str]:
        lines: List[str] = []
        for title, tag in INSIGHTS_SECTIONS:
            matched = self._insights_indicators(tag, kpi_only)
            if title == "Ecosystem":
                lines.extend(self._ecosystem_section(matched, definitions, included))
            else:
                included.extend(matched)
                lines.append(f"## {title}")
                lines.append("")
                if not matched:
                    lines.append(f"No {title} indicators match this filter.")
                    lines.append("")
                else:
                    for indicator in matched:
                        lines.extend(self._indicator_block(indicator, definitions))
        lines.extend(self._published_spec_section(definitions, included))
        lines.extend(self._meeting_section())
        lines.extend(self._publication_section(include_publications))
        return lines

    def _insights_indicators(self, tag: str, kpi_only: bool) -> List[KPIIndicator]:
        indicators = self.data_service.get_standards_development_indicators(STEWARD, tag)
        if kpi_only:
            indicators = [indicator for indicator in indicators if self._is_kpi(indicator)]
        return indicators

    def _ecosystem_section(
        self,
        matched: Sequence[KPIIndicator],
        definitions: Dict[str, List[str]],
        included: List[KPIIndicator],
    ) -> List[str]:
        lines = ["## Ecosystem", ""]
        if not matched:
            lines.append("No Ecosystem indicators match this filter.")
            lines.append("")
            return lines

        composites = [
            indicator
            for indicator_id in PACKAGE_VERSION_IDS
            if (indicator := self.data_service.get_indicator_by_id(indicator_id))
        ]
        included.extend(composites)
        lines.extend(
            [
                "### Composite charts",
                "",
                "The Ecosystem section draws two combined charts from these series. Each series is listed once.",
                "",
                "- Package versions: New R4, R4B, R5 uses indicators 49, 50, and 51.",
                "- Package versions: Total R4, R4B, R5 uses indicators 52, 53, and 54.",
                "",
            ]
        )
        if any(not self._is_kpi(indicator) for indicator in composites):
            lines.append(
                "These package-version series stay on the dashboard when Show KPIs Only is on, "
                "as long as another Ecosystem indicator is still visible."
            )
            lines.append("")
        for indicator in composites:
            lines.extend(self._indicator_block(indicator, definitions))

        rest = [indicator for indicator in matched if indicator.id not in PACKAGE_VERSION_IDS]
        included.extend(rest)
        if rest:
            lines.append("### Other Ecosystem indicators")
            lines.append("")
            for indicator in rest:
                lines.extend(self._indicator_block(indicator, definitions))
        return lines

    def _published_spec_section(
        self,
        definitions: Dict[str, List[str]],
        included: List[KPIIndicator],
    ) -> List[str]:
        lines = [
            "## Published specifications by realm",
            "",
            "The dashboard chart stacks U.S. Realm (ID 47) and Universal Realm (ID 48) "
            "under Total published specifications (ID 27). This chart stays visible when Show KPIs Only is on.",
            "",
        ]
        for indicator_id in PUBLISHED_SPEC_IDS:
            indicator = self.data_service.get_indicator_by_id(indicator_id)
            if not indicator:
                lines.append(f"Indicator {indicator_id} is missing.")
                lines.append("")
                continue
            included.append(indicator)
            lines.extend(self._indicator_block(indicator, definitions))
        return lines

    def _meeting_section(self) -> List[str]:
        lines = [
            "## Working Group Meeting locations",
            "",
            "Host for the trimester Working Group Meeting. The dashboard can overlay these on the charts. The indicator values above are unchanged.",
            "",
        ]
        try:
            locations = self.meeting_locations_service.get_locations()
        except Exception as exc:
            lines.append(f"Meeting locations could not be loaded: {exc}")
            lines.append("")
            return lines
        if not locations:
            lines.append("No meeting locations are loaded.")
            lines.append("")
            return lines

        lines.append("| Period | Location |")
        lines.append("| --- | --- |")
        for period in sorted(locations):
            lines.append(f"| {self._cell(period)} | {self._cell(self._format_location(locations[period]))} |")
        lines.append("")
        return lines

    def _format_location(self, location: Dict[str, Any]) -> str:
        kind = location.get("kind")
        if kind == "virtual":
            label = "Virtual"
        elif kind == "hybrid":
            label = "Hybrid"
        else:
            label = (location.get("country") or "Unknown").strip() or "Unknown"
        meeting = (location.get("meeting") or "").strip()
        if meeting and meeting.lower() not in label.lower():
            label = f"{label} — {meeting}"
        return label

    def _publication_section(self, include_publications: bool) -> List[str]:
        lines = [
            "## Published standards",
            "",
            "Counts of HL7 publications (publication status only; reaffirmations excluded).",
            "",
        ]
        try:
            years = self.published_standards_service.get_available_years()
        except Exception as exc:
            lines.append(f"Publication list could not be loaded: {exc}")
            lines.append("")
            return lines
        if not years:
            lines.append("No publication years are loaded.")
            lines.append("")
            return lines

        by_year = {
            year: self.published_standards_service.get_standards_for_year(year) for year in years
        }
        family_counts: Counter = Counter()
        realm_counts: Counter = Counter()
        lines.append("| Year | Publications |")
        lines.append("| --- | --- |")
        for year in years:
            standards = by_year[year]
            lines.append(f"| {year} | {len(standards)} |")
            for standard in standards:
                family_counts[standard.get("family") or "(blank)"] += 1
                realm_counts[standard.get("realm") or "(blank)"] += 1
        lines.append("")
        lines.extend(self._count_table("By family", family_counts))
        lines.extend(self._count_table("By realm", realm_counts))

        latest = years[-1]
        if include_publications:
            lines.append("### Titles by year")
            lines.append("")
            for year in years:
                lines.extend(self._title_list(year, by_year[year]))
        else:
            lines.append(f"### Titles in {latest}")
            lines.append("")
            lines.append("Earlier years are counts only. Ask again with the full publication list to include every title.")
            lines.append("")
            lines.extend(self._title_list(latest, by_year[latest], heading=False))
        return lines

    def _count_table(self, title: str, counts: Counter) -> List[str]:
        lines = [f"### {title}", "", "| Name | Count |", "| --- | --- |"]
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower())):
            lines.append(f"| {self._cell(name)} | {count} |")
        lines.append("")
        return lines

    def _title_list(self, year: int, standards: Sequence[Dict[str, Any]], heading: bool = True) -> List[str]:
        lines: List[str] = []
        if heading:
            lines.append(f"#### {year}")
            lines.append("")
        if not standards:
            lines.append("No publications.")
            lines.append("")
            return lines
        for standard in standards:
            name = self._plain(standard.get("name") or "")
            family = self._plain(standard.get("family") or "")
            realm = self._plain(standard.get("realm") or "")
            date = self._plain(standard.get("date") or "")
            meta = ", ".join(part for part in (family, realm) if part)
            suffix = f" ({meta})" if meta else ""
            prefix = f"{date}: " if date else ""
            lines.append(f"- {prefix}{name}{suffix}")
        lines.append("")
        return lines

    def _indicator_block(
        self,
        indicator: KPIIndicator,
        definitions: Dict[str, List[str]],
        heading_level: int = 3,
    ) -> List[str]:
        heading = "#" * heading_level
        lines = [
            f"{heading} {self._plain(indicator.name)} (ID {indicator.id})",
            "",
            f"- Unit: {self._unit_label(indicator)}",
            f"- Tags: {', '.join(indicator.tags) if indicator.tags else 'none'}",
            f"- Better when: {indicator.trend_direction or 'higher'}",
            f"- {self._target_label(indicator)}",
        ]
        definition = self._definition_for(indicator, definitions)
        if definition:
            lines.append(f"- Definition: {self._plain(definition)}")
        lines.append("")
        lines.extend(self._measurement_table(indicator))
        lines.append("")
        return lines

    def _unit_label(self, indicator: KPIIndicator) -> str:
        unit = (indicator.unit or "").strip()
        measure_type = (indicator.type or "").strip()
        if unit and measure_type:
            return f"{unit} ({measure_type})"
        return unit or measure_type or "unspecified"

    def _target_label(self, indicator: KPIIndicator) -> str:
        if indicator.targets:
            operation = indicator.target_operation or "unspecified operation"
            parts = [
                f"{year}: {self._format_number(value)}"
                for year, value in sorted(indicator.targets.items())
            ]
            return f"Annual targets ({operation}): {', '.join(parts)}"
        if indicator.target is not None:
            return f"Target: {self._format_number(indicator.target)}"
        return "Annual target: none"

    def _definition_for(
        self, indicator: KPIIndicator, definitions: Dict[str, List[str]]
    ) -> str:
        options = definitions.get(indicator.id, [])
        if not options:
            description = (indicator.description or "").strip()
            if description and description.lower() != indicator.name.lower():
                return description
            return ""
        if len(options) == 1:
            return options[0]
        name = indicator.name.lower()
        for option in options:
            match = _BOLD_RE.search(option)
            label = (match.group(1) if match else option).lower()
            if name in label or label in name:
                return option
        return options[0]

    def _measurement_table(self, indicator: KPIIndicator) -> List[str]:
        rows = []
        any_notes = False
        for period in sorted(indicator.measurements):
            measurement = indicator.measurements[period]
            note = self._plain(measurement.notes or "")
            if note:
                any_notes = True
            rows.append((period, measurement.value, measurement.target, note))

        if any_notes:
            lines = ["| Period | Value | Period target | Notes |", "| --- | --- | --- | --- |"]
            for period, value, target, note in rows:
                lines.append(
                    f"| {self._cell(period)} | {self._format_number(value)} | {self._format_number(target)} | {self._cell(note)} |"
                )
        else:
            lines = ["| Period | Value | Period target |", "| --- | --- | --- |"]
            for period, value, target, _note in rows:
                lines.append(
                    f"| {self._cell(period)} | {self._format_number(value)} | {self._format_number(target)} |"
                )
        if not rows:
            lines.append("|  |  |  |")
        return lines

    def _image_file(self, filename: str) -> Optional[Path]:
        name = Path(filename).name
        if not name or name != filename.strip():
            return None
        path = IMAGE_DIR / name
        if path.is_file():
            return path
        return None

    def _write_package(
        self, scope: str, prompt_text: str, attachments: Sequence[Dict[str, Any]]
    ) -> Path:
        package_file = PROMPT_DIR / f"standards_development_llm_prompt_{scope}.zip"
        with zipfile.ZipFile(package_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("prompt.md", prompt_text)
            for attachment in attachments:
                if not attachment.get("included"):
                    continue
                payload = attachment.get("bytes")
                if payload:
                    archive.writestr(attachment["path"], payload)
                    continue
                source = self._image_file(attachment["filename"])
                if source:
                    archive.write(source, arcname=attachment["path"])
        return package_file

    def _chart_attachments(self, charts: Sequence[Any]) -> List[Dict[str, Any]]:
        attachments = []
        seen = set()
        for chart in charts[:40]:
            filename = self._safe_png_name(self._chart_field(chart, "filename"))
            title = self._plain(self._chart_field(chart, "title") or filename or "Chart")
            encoded = self._chart_field(chart, "data")
            if not filename or not encoded:
                continue
            try:
                payload = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                continue
            if len(payload) > 8_000_000 or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                continue
            unique = filename
            suffix = 2
            while unique in seen:
                unique = f"{Path(filename).stem}-{suffix}.png"
                suffix += 1
            seen.add(unique)
            attachments.append(
                {
                    "indicator": title,
                    "filename": unique,
                    "path": f"charts/{unique}",
                    "included": True,
                    "bytes": payload,
                }
            )
        return attachments

    @staticmethod
    def _chart_field(chart: Any, name: str) -> str:
        if isinstance(chart, dict):
            value = chart.get(name, "")
        else:
            value = getattr(chart, name, "")
        return "" if value is None else str(value)

    @staticmethod
    def _safe_png_name(filename: str) -> Optional[str]:
        stem = Path(filename or "").name
        if stem.lower().endswith(".png"):
            stem = stem[:-4]
        stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem).strip("._ ")
        if not stem:
            return None
        return f"{stem[:120]}.png"

    def _attachments(self, indicators: Sequence[KPIIndicator]) -> List[Dict[str, Any]]:
        seen = set()
        attachments = []
        for indicator in indicators:
            filename = (indicator.image or "").strip()
            if not filename or filename in seen:
                continue
            seen.add(filename)
            source = self._image_file(filename)
            attachments.append(
                {
                    "indicator_id": indicator.id,
                    "indicator": indicator.name,
                    "filename": Path(filename).name,
                    "path": f"images/{Path(filename).name}",
                    "included": source is not None,
                }
            )
        return attachments

    def _attachment_lines(self, attachments: Sequence[Dict[str, Any]], kind: str = "screenshots") -> List[str]:
        included = [item for item in attachments if item.get("included")]
        if kind == "charts":
            heading = "## Chart images"
            empty = "No charts from the insights page were included with this prompt."
            intro = (
                "The downloaded zip has this prompt as `prompt.md` and these chart images in `charts/`. "
                "They are the charts visible on the Standards Development Insights page when the prompt was created. "
                "Upload the image files with this prompt when the model can read images. "
                "The tables above already contain the numbers."
            )
        else:
            heading = "## Visual attachments"
            empty = "No indicator screenshots are included with this prompt."
            intro = (
                "The downloaded zip has this prompt as `prompt.md` and these screenshots in `images/`. "
                "Upload the image files with this prompt when the model can read images. "
                "The tables above already contain the numbers."
            )
        lines = [heading, ""]
        if not included:
            lines.append(empty)
            lines.append("")
            return lines
        lines.extend([intro, ""])
        for attachment in included:
            indicator_id = attachment.get("indicator_id")
            label = attachment["indicator"]
            if indicator_id:
                label = f"{label} (ID {indicator_id})"
            lines.append(f"- {label}: `{attachment['path']}`")
        missing = [item for item in attachments if not item.get("included")]
        if missing:
            lines.append("")
            lines.append("These screenshots were listed on the indicator but the image file was not available:")
            for attachment in missing:
                lines.append(
                    f"- {attachment['indicator']} (ID {attachment['indicator_id']}): `{attachment['filename']}`"
                )
        lines.append("")
        return lines

    def _question_lines(self, question: str) -> List[str]:
        cleaned = (question or "").strip()
        lines = ["## Question", ""]
        if cleaned:
            lines.append(cleaned)
            lines.append("")
            lines.append("Answer this question using only the context and data above.")
        else:
            lines.append(
                "No question was provided. Treat the material above as a context pack. "
                "Wait for a question, and do not write an unsolicited analysis."
            )
        lines.append("")
        return lines

    @staticmethod
    def _is_kpi(indicator: KPIIndicator) -> bool:
        return any(tag.upper() == "KPI" for tag in indicator.tags)

    @staticmethod
    def _format_number(value: Optional[float]) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value)

    @classmethod
    def _plain(cls, value: str) -> str:
        text = _TAG_RE.sub(" ", value or "")
        text = html.unescape(text)
        return _WHITESPACE_RE.sub(" ", text).strip()

    @classmethod
    def _cell(cls, value: str) -> str:
        return cls._plain(value).replace("|", "\\|")
