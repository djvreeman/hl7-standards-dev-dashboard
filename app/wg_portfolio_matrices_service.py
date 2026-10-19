"""
Serve WG portfolio count matrices:

- FHIR base resources owned by work group × FHIR core version
- Specifications balloted by work group × trimester
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_FHIR_PATH = Path("data/standards-development/fhir_resource_ownership_matrix.json")
DEFAULT_BALLOT_PATH = Path("data/standards-development/wg_ballot_specs_matrix.json")
DEFAULT_STATUS_PATH = Path("data/standards-development/wg_status.json")


class WgPortfolioMatricesService:
    def __init__(
        self,
        fhir_path: Optional[Path] = None,
        ballot_path: Optional[Path] = None,
        status_path: Optional[Path] = None,
    ):
        self.fhir_path = Path(fhir_path) if fhir_path else DEFAULT_FHIR_PATH
        self.ballot_path = Path(ballot_path) if ballot_path else DEFAULT_BALLOT_PATH
        self.status_path = Path(status_path) if status_path else DEFAULT_STATUS_PATH
        self._fhir: Optional[Dict[str, Any]] = None
        self._fhir_mtime: Optional[float] = None
        self._ballot: Optional[Dict[str, Any]] = None
        self._ballot_mtime: Optional[float] = None
        self._status: Optional[Dict[str, Any]] = None
        self._status_mtime: Optional[float] = None

    def _load_json(self, path: Path, cache_attr: str, mtime_attr: str) -> Dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(f"Matrix data not found at {path}")
        mtime = path.stat().st_mtime
        cached = getattr(self, cache_attr)
        cached_mtime = getattr(self, mtime_attr)
        if cached is not None and cached_mtime == mtime:
            return cached
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        setattr(self, cache_attr, payload)
        setattr(self, mtime_attr, mtime)
        return payload

    def get_fhir_resource_ownership(self) -> Dict[str, Any]:
        return self._load_json(self.fhir_path, "_fhir", "_fhir_mtime")

    def get_ballot_specs(self) -> Dict[str, Any]:
        return self._load_json(self.ballot_path, "_ballot", "_ballot_mtime")

    def get_workgroup_status(self) -> Dict[str, Any]:
        return self._load_json(self.status_path, "_status", "_status_mtime")
