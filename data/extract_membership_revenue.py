#!/usr/bin/env python3
"""
Extract monthly membership revenue totals from HL7 membership revenue workbooks.

Reads the "Revenue Breakdown" sheet and pulls the Membership Class pivot
"Grand Total" (Affiliate + Individual + Organizational dues).

Month is parsed from the filename (e.g. 2026_Membership_Revenues_Apr2026.xlsx -> 2026 04).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

MONTH_ABBREV = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

FILENAME_MONTH_RE = re.compile(
    r"_(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})",
    re.IGNORECASE,
)

REVENUE_SHEET = "Revenue Breakdown"
MEMBERSHIP_CLASS_LABEL = "Membership Class"
GRAND_TOTAL_LABEL = "Grand Total"


def parse_month_from_filename(filename: str) -> str:
    """Return month as 'YYYY MM' from a workbook filename."""
    match = FILENAME_MONTH_RE.search(filename)
    if not match:
        raise ValueError(
            f"Cannot parse month from filename '{filename}' "
            f"(expected pattern like *_Apr2026.xlsx)"
        )
    month_num = MONTH_ABBREV[match.group(1).lower()]
    year = int(match.group(2))
    return f"{year} {month_num:02d}"


def extract_grand_total_dues(workbook_path: Path) -> float:
    """Read Membership Class Grand Total from Revenue Breakdown."""
    df = pd.read_excel(workbook_path, sheet_name=REVENUE_SHEET, header=None)

    header_row = None
    for row_idx in range(len(df)):
        label = df.iat[row_idx, 5] if df.shape[1] > 5 else None
        if isinstance(label, str) and label.strip() == MEMBERSHIP_CLASS_LABEL:
            header_row = row_idx
            break

    if header_row is None:
        raise ValueError(
            f"'{workbook_path.name}': could not find '{MEMBERSHIP_CLASS_LABEL}' "
            f"on sheet '{REVENUE_SHEET}'"
        )

    for row_idx in range(header_row + 1, min(header_row + 12, len(df))):
        label = df.iat[row_idx, 5]
        if isinstance(label, str) and label.strip() == GRAND_TOTAL_LABEL:
            value = df.iat[row_idx, 6]
            if value is None or (isinstance(value, float) and pd.isna(value)):
                raise ValueError(
                    f"'{workbook_path.name}': Grand Total cell is empty"
                )
            return float(value)

    raise ValueError(
        f"'{workbook_path.name}': could not find '{GRAND_TOTAL_LABEL}' "
        f"after '{MEMBERSHIP_CLASS_LABEL}'"
    )


def extract_row(workbook_path: Path) -> dict[str, str | int]:
    month = parse_month_from_filename(workbook_path.name)
    total = round(extract_grand_total_dues(workbook_path))
    return {
        "month": month,
        "total_membership_revenue": total,
        "source_file": workbook_path.name,
    }


def discover_workbooks(input_dir: Path, paths: Optional[Iterable[Path]]) -> list[Path]:
    if paths:
        workbooks = [Path(p).resolve() for p in paths]
    else:
        workbooks = sorted(input_dir.glob("*.xlsx"))
    if not workbooks:
        raise FileNotFoundError(f"No .xlsx files found in {input_dir}")
    return workbooks


def write_csv(rows: list[dict[str, str | int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["month", "total_membership_revenue", "source_file"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    default_input = repo_root / "data" / "member-revenue"
    default_output = repo_root / "data" / "processed" / "membership_revenue_monthly.csv"

    parser = argparse.ArgumentParser(
        description="Extract monthly membership revenue totals to CSV."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=default_input,
        help=f"Directory containing membership revenue .xlsx files (default: {default_input})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Output CSV path (default: {default_output})",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional specific workbook paths (default: all .xlsx in --input-dir)",
    )
    args = parser.parse_args(argv)

    try:
        workbooks = discover_workbooks(args.input_dir, args.files or None)
        rows = [extract_row(path) for path in workbooks]
        rows.sort(key=lambda row: row["month"])
        write_csv(rows, args.output)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(rows)} row(s) to {args.output}")
    for row in rows:
        print(f"  {row['month']}  {row['total_membership_revenue']:,}  ({row['source_file']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
