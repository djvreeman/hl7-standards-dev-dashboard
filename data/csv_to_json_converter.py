#!/usr/bin/env python3
"""
CSV to JSON Converter for HL7 KPI Dashboard
Converts raw CSV data to the proper JSON structure for the dashboard.
"""

import csv
import json
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
import markdown

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import KPIData, KPIMetadata, KPIIndicator, KPIMeasurement

class CSVToJSONConverter:
    def __init__(self, csv_path: str = "data/raw/all_kpis.csv", 
                 definitions_path: str = "data/raw/indicator-definitions.csv",
                 published_standards_csv: str = "data/raw/HL7 Standards Tracking - Stats Metrics - Published Specifications.csv"):
        self.csv_path = Path(csv_path)
        self.definitions_path = Path(definitions_path)
        self.published_standards_csv = Path(published_standards_csv)
        self.definitions = {}
        self._load_definitions()
    
    def _load_definitions(self):
        """Load indicator definitions from CSV"""
        if not self.definitions_path.exists():
            return
        
        with open(self.definitions_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.definitions[row['ID']] = row['Definition']
                # Debug: print the full definition to check for truncation
                print(f"Loaded definition for {row['ID']}: {row['Definition'][:100]}...")
    
    def _copy_indicator_image(self, image_filename: str) -> Optional[str]:
        """Copy indicator image from data/raw to static/indicators if it exists"""
        if not image_filename or not image_filename.strip():
            return None
        
        source_path = Path("data/raw") / image_filename.strip()
        target_path = Path("static/indicators") / image_filename.strip()
        
        if source_path.exists():
            try:
                # Create target directory if it doesn't exist
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy the image
                shutil.copy2(source_path, target_path)
                print(f"Copied image: {image_filename}")
                return image_filename.strip()
            except Exception as e:
                print(f"Error copying image {image_filename}: {e}")
                return None
        else:
            print(f"Image file not found: {source_path}")
            return None
    
    @staticmethod
    def _period_sort_key(time_period: str) -> Tuple[int, int]:
        """Stable ordering for HL7 quarters like '2026-T1' for tie-breaking newer periods."""
        if not time_period or "-" not in time_period:
            return (0, 0)
        year_str, rest = time_period.split("-", 1)
        if not rest.startswith("T"):
            try:
                return (int(year_str), 0)
            except ValueError:
                return (0, 0)
        q = rest[1:]
        try:
            return (int(year_str), int(q))
        except ValueError:
            return (0, 0)
    
    def _indicator_image_best(
        self, current: Optional[Tuple[str, str]], time_period: str, image_filename: str
    ) -> Tuple[str, str]:
        """Keep the image tied to the latest time_period (CSV row order is not guaranteed)."""
        if current is None:
            return (time_period, image_filename)
        prev_period, prev_name = current
        if self._period_sort_key(time_period) >= self._period_sort_key(prev_period):
            return (time_period, image_filename)
        return current
    
    def _get_description(self, indicator_id: str, indicator_name: str) -> str:
        """Get description for an indicator, falling back to name if no definition exists"""
        if indicator_id in self.definitions:
            # Extract description from the definition (remove markdown formatting)
            definition = self.definitions[indicator_id]
            
            # Debug: print the full definition for problematic IDs
            if indicator_id == "HL7-2":
                print(f"Full definition for {indicator_id}: {repr(definition)}")
            
            # Remove markdown formatting and extract the description
            if "**" in definition:
                # Extract text after the bold indicator name
                parts = definition.split("**")
                if len(parts) >= 3:
                    # Clean up the description text
                    description = parts[2].strip(": ").strip()
                    # Remove any remaining markdown formatting
                    description = description.replace("**", "").replace("*", "")
                    
                    # Debug: print the extracted description for problematic IDs
                    if indicator_id == "HL7-2":
                        print(f"Extracted description for {indicator_id}: {repr(description)}")
                    
                    return description
            else:
                # If no bold formatting, return the whole definition
                return definition.replace("**", "").replace("*", "")
        return indicator_name
    
    def _determine_unit(self, indicator_type: str, indicator_name: str) -> str:
        """Determine the unit based on type and name"""
        if indicator_type == "%":
            return "percentage"
        elif indicator_type == "N":
            if "members" in indicator_name.lower():
                return "members"
            elif "specifications" in indicator_name.lower() or "standards" in indicator_name.lower():
                return "specifications"
            elif "issues" in indicator_name.lower():
                return "issues"
            elif "tracks" in indicator_name.lower():
                return "tracks"
            elif "countries" in indicator_name.lower():
                return "countries"
            elif "participants" in indicator_name.lower():
                return "participants"
            elif "months" in indicator_name.lower():
                return "months"
            else:
                return "count"
        elif indicator_type == "Ave per Item":
            return "average"
        else:
            return "count"
    
    def _determine_trend_direction(self, indicator_name: str, indicator_type: str) -> str:
        """Determine whether higher or lower values are better for this indicator (fallback when Direction field is not provided)"""
        name_lower = indicator_name.lower()
        
        # Special cases where higher values are better (override any keyword matching)
        higher_is_better_special_cases = [
            "issue submitters",
            "active participants",
            "active members",
            "co-chairs",
            "track leads",
            "balloters",
            "citations",
            "published specifications",
            "new projects",
            "work groups in good health",
            "participants in courses",
            "member satisfaction",
            "operating reserves"
        ]
        
        # Check special cases first
        for case in higher_is_better_special_cases:
            if case in name_lower:
                return "higher"
        
        # Indicators where lower values are better
        lower_is_better_keywords = [
            "variance from budget",
            "error",
            "failure",
            "downtime",
            "response time",
            "cost",
            "expense",
            "debt",
            "deficit",
            "loss",
            "complaint",
            "issue rate",
            "issue count",
            "issue frequency",
            "problem",
            "delay",
            "wait time",
            "queue",
            "backlog"
        ]
        
        # Check if any lower-is-better keywords are in the indicator name
        for keyword in lower_is_better_keywords:
            if keyword in name_lower:
                return "lower"
        
        # Default to higher is better for most indicators
        return "higher"
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown text to HTML"""
        if not markdown_text or not markdown_text.strip():
            return ""
        
        # Configure markdown with safe extensions
        md = markdown.Markdown(
            extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.nl2br',
                'markdown.extensions.sane_lists'
            ],
            output_format='html'
        )
        
        # Convert markdown to HTML
        html = md.convert(markdown_text.strip())
        
        # Clean up any potential security issues (basic sanitization)
        # Remove script tags and other potentially dangerous elements
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<object[^>]*>.*?</object>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<embed[^>]*>', '', html, flags=re.IGNORECASE)
        
        return html
    
    def _date_to_time_period(self, date_obj: datetime) -> str:
        """Convert a datetime to a time period string (e.g., '2025-T1')
        
        Trimesters:
        - T1: January-March (Q1)
        - T2: April-June (Q2)
        - T3: July-September (Q3)
        """
        year = date_obj.year
        month = date_obj.month
        
        if month >= 1 and month <= 3:
            trimester = "T1"
        elif month >= 4 and month <= 6:
            trimester = "T2"
        elif month >= 7 and month <= 9:
            trimester = "T3"
        else:  # October-December
            # For Q4 (Oct-Dec), assign to T3 of the current year
            # Note: This may need adjustment based on actual fiscal year or reporting period definitions
            trimester = "T3"
        
        return f"{year}-{trimester}"
    
    def _parse_date_from_csv(self, date_str: str, fy_str: str = None) -> Optional[datetime]:
        """Parse date string from published standards CSV"""
        if not date_str or not date_str.strip():
            # Fallback to FY if Date is empty
            if fy_str:
                try:
                    # Use January 1st of the fiscal year as a fallback
                    return datetime(int(fy_str), 1, 1)
                except ValueError:
                    return None
            return None
        
        date_str = date_str.strip()
        
        # Try parsing as M/D/YYYY
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            pass
        
        # Try parsing as M/D/YY
        try:
            return datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            pass
        
        # Fallback to FY
        if fy_str:
            try:
                return datetime(int(fy_str), 1, 1)
            except ValueError:
                pass
        
        return None
    
    def _populate_published_specs_indicators(self, dry_run: bool = False) -> Dict[str, Any]:
        """Populate indicators 27, 28, 47, 48 from published standards CSV
        
        Indicator 27: All published specifications
        Indicator 28: Accelerator-led published specifications  
        Indicator 47: U.S. Realm published specifications
        Indicator 48: Universal Realm published specifications
        
        Args:
            dry_run: If True, return what would be updated without actually updating the CSV
            
        Returns:
            Dictionary with update statistics and details
        """
        if not self.published_standards_csv.exists():
            warning_msg = f"Warning: Published standards CSV not found: {self.published_standards_csv}"
            print(warning_msg)
            return {"error": warning_msg, "updates": [], "summary": {}}
        
        # Read the current all_kpis.csv to preserve other data
        rows = []
        fieldnames = None
        
        with open(self.csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # Count publications by time period
        # Structure: {time_period: {indicator_id: count}}
        counts = defaultdict(lambda: {
            '27': 0,  # All published specifications
            '28': 0,  # Accelerator-led published specifications
            '47': 0,  # U.S. Realm published specifications
            '48': 0   # Universal Realm published specifications
        })
        
        # Read published standards CSV directly to get all the data we need
        with open(self.published_standards_csv, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Only include publications (exclude Reaffirmations)
                pub_status = row.get('Pub Status', '').strip()
                if pub_status != 'Publication':
                    continue
                
                # Get time period from Trimester field (e.g., "2024-T3" or "2019 T1")
                trimester = row.get('Trimester', '').strip()
                if not trimester:
                    continue
                
                # Normalize time period format to match all_kpis.csv format (YYYY-TN)
                # Handle both formats: "2024-T3" and "2019 T1"
                time_period = trimester.replace(' ', '-').upper()
                # Ensure format is YYYY-TN (e.g., "2024-T3")
                if not time_period or '-' not in time_period:
                    continue
                
                # Get realm and accelerator
                realm = row.get('Realm', '').strip()
                accelerator = row.get('Accelerator', '').strip()
                
                # Count for indicator 27 (all published specifications)
                counts[time_period]['27'] += 1
                
                # Count for indicator 28 (accelerator-led)
                if accelerator:
                    counts[time_period]['28'] += 1
                
                # Count for indicator 47 (U.S. Realm)
                if realm == 'United States':
                    counts[time_period]['47'] += 1
                
                # Count for indicator 48 (Universal Realm)
                if realm == 'Universal':
                    counts[time_period]['48'] += 1
        
        # Track updates for reporting
        updates = []
        comparisons = []  # For QA comparison of indicators 27 and 28
        updated_rows = []
        updated_periods = set()
        existing_periods_by_indicator = defaultdict(set)
        
        # First pass: collect existing periods and update values.
        # Indicators 27/28/47/48 are derived from the published-standards CSV, so
        # periods no longer present in that source are removed (prevents stale
        # points like a leftover 2026-T3 after the export was truncated to T2).
        for row in rows:
            indicator_id = row.get('ID', '').strip()
            time_period = row.get('Time Period', '').strip()
            
            if indicator_id in ['27', '28', '47', '48']:
                if time_period not in counts:
                    updates.append({
                        'indicator_id': indicator_id,
                        'indicator_name': row.get('Indicator', ''),
                        'time_period': time_period,
                        'old_value': row.get('Value', '').strip() or '(empty)',
                        'new_value': '(removed)',
                        'action': 'removed_stale_period'
                    })
                    continue

                existing_periods_by_indicator[indicator_id].add(time_period)
                new_value = counts[time_period][indicator_id]
                current_value = row.get('Value', '').strip()
                
                # For indicators 27 and 28: Compare existing values with calculated values for QA, then update
                if indicator_id in ['27', '28']:
                    if current_value:
                        # Compare existing value with calculated value for QA
                        try:
                            existing_num = float(current_value)
                            calculated_num = float(new_value)
                            matches = existing_num == calculated_num
                            
                            comparisons.append({
                                'indicator_id': indicator_id,
                                'indicator_name': row.get('Indicator', ''),
                                'time_period': time_period,
                                'existing_value': existing_num,
                                'calculated_value': calculated_num,
                                'matches': matches,
                                'difference': calculated_num - existing_num if not matches else 0
                            })
                            
                            # Always update with calculated value (not just fill gaps)
                            row['Value'] = str(new_value) if new_value > 0 else ''
                            updated_periods.add((indicator_id, time_period))
                            action = 'updated' if not matches else 'verified'
                            updates.append({
                                'indicator_id': indicator_id,
                                'indicator_name': row.get('Indicator', ''),
                                'time_period': time_period,
                                'old_value': str(existing_num),
                                'new_value': str(new_value) if new_value > 0 else '(empty)',
                                'action': action
                            })
                        except ValueError:
                            # If existing value can't be parsed, treat as empty and update
                            row['Value'] = str(new_value) if new_value > 0 else ''
                            updated_periods.add((indicator_id, time_period))
                            updates.append({
                                'indicator_id': indicator_id,
                                'indicator_name': row.get('Indicator', ''),
                                'time_period': time_period,
                                'old_value': current_value or '(empty)',
                                'new_value': str(new_value) if new_value > 0 else '(empty)',
                                'action': 'filled_gap'
                            })
                    else:
                        # Empty value - fill gap
                        row['Value'] = str(new_value) if new_value > 0 else ''
                        updated_periods.add((indicator_id, time_period))
                        updates.append({
                            'indicator_id': indicator_id,
                            'indicator_name': row.get('Indicator', ''),
                            'time_period': time_period,
                            'old_value': '(empty)',
                            'new_value': str(new_value) if new_value > 0 else '(empty)',
                            'action': 'filled_gap'
                        })
                else:
                    # For indicators 47 and 48, update if value is empty or if we have new data
                    if not current_value:
                        row['Value'] = str(new_value) if new_value > 0 else ''
                        updated_periods.add((indicator_id, time_period))
                        updates.append({
                            'indicator_id': indicator_id,
                            'indicator_name': row.get('Indicator', ''),
                            'time_period': time_period,
                            'old_value': '(empty)',
                            'new_value': str(new_value) if new_value > 0 else '(empty)',
                            'action': 'filled_gap'
                        })
                    elif indicator_id in ['47', '48']:
                        # Keep 47/48 aligned with source counts (including zero → empty)
                        old_val = current_value or '(empty)'
                        row['Value'] = str(new_value) if new_value > 0 else ''
                        updated_periods.add((indicator_id, time_period))
                        updates.append({
                            'indicator_id': indicator_id,
                            'indicator_name': row.get('Indicator', ''),
                            'time_period': time_period,
                            'old_value': old_val,
                            'new_value': str(new_value) if new_value > 0 else '(empty)',
                            'action': 'updated' if old_val != '(empty)' else 'filled_gap'
                        })
            
            updated_rows.append(row)
        
        # Second pass: Add missing time periods present in the published-standards source
        all_available_periods = set(counts.keys())
        
        for indicator_id in ['27', '28', '47', '48']:
            existing_periods = existing_periods_by_indicator.get(indicator_id, set())
            missing_periods = all_available_periods - existing_periods
            
            for time_period in missing_periods:
                # Find a template row for this indicator to copy metadata
                template_row = next((row for row in rows if row.get('ID', '').strip() == indicator_id), None)
                if template_row:
                    new_row = template_row.copy()
                    new_row['Time Period'] = time_period
                    new_value = counts[time_period][indicator_id]
                    new_row['Value'] = str(new_value) if new_value > 0 else ''
                    updated_rows.append(new_row)
                    updated_periods.add((indicator_id, time_period))
                    updates.append({
                        'indicator_id': indicator_id,
                        'indicator_name': template_row.get('Indicator', ''),
                        'time_period': time_period,
                        'old_value': '(missing)',
                        'new_value': str(new_value) if new_value > 0 else '(empty)',
                        'action': 'added_period'
                    })
        
        # Prepare summary statistics
        summary = {
            'total_updates': len(updates),
            'by_indicator': defaultdict(int),
            'by_action': defaultdict(int),
            'by_time_period': defaultdict(int),
            'qa_comparisons': {
                'total_comparisons': len(comparisons),
                'matches': sum(1 for c in comparisons if c['matches']),
                'mismatches': sum(1 for c in comparisons if not c['matches']),
                'comparisons': comparisons
            }
        }
        
        for update in updates:
            summary['by_indicator'][update['indicator_id']] += 1
            summary['by_action'][update['action']] += 1
            summary['by_time_period'][update['time_period']] += 1
        
        # Convert defaultdicts to regular dicts for JSON serialization
        summary['by_indicator'] = dict(summary['by_indicator'])
        summary['by_action'] = dict(summary['by_action'])
        summary['by_time_period'] = dict(summary['by_time_period'])
        
        if not dry_run:
            # Write updated CSV back
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_rows)
            
            print(f"Updated indicators 27, 28, 47, 48 from published standards CSV")
            print(f"Updated {len(updated_periods)} time period values")
            
            # Print QA comparison results
            if comparisons:
                matches = sum(1 for c in comparisons if c['matches'])
                mismatches = sum(1 for c in comparisons if not c['matches'])
                print(f"QA Comparison: {matches} matches, {mismatches} mismatches for indicators 27 & 28")
        else:
            print(f"DRY RUN: Would update indicators 27, 28, 47, 48 from published standards CSV")
            print(f"Would update {len(updated_periods)} time period values")
            
            # Print QA comparison results for dry run
            if comparisons:
                matches = sum(1 for c in comparisons if c['matches'])
                mismatches = sum(1 for c in comparisons if not c['matches'])
                print(f"QA Comparison: {matches} matches, {mismatches} mismatches for indicators 27 & 28")
                if mismatches > 0:
                    print("WARNING: Mismatches found! Please review before applying changes.")
        
        return {
            'updates': updates,
            'summary': summary,
            'total_periods_updated': len(updated_periods),
            'qa_comparisons': comparisons
        }
    
    def convert(self) -> KPIData:
        """Convert CSV data to JSON structure"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        indicators = {}
        time_periods = set()
        domains = set()
        stewards = set()
        # Per-indicator: (time_period, image_base_name) — use image from newest period, not last CSV row
        best_indicator_image: Dict[str, Tuple[str, str]] = {}
        
        # Try to read with UTF-8, fallback to latin-1 or error handling if needed
        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    indicator_id = row['ID']
                    time_period = row['Time Period']
                    domain = row['Domain']
                    indicator_name = row['Indicator']
                    indicator_type = row['Type']
                    value_str = row['Value']
                    notes = row['Notes'] if row['Notes'] else None
                    steward_str = row['Steward']
                    target_str = row['Target']
                    target_type = row.get('Target Type', '').lower()  # Normalize to lowercase
                    target_operation = row.get('Target Operation', '').lower() if row.get('Target Operation') else ''  # New field
                    unit = row.get('Unit', '')  # New field
                    csv_type = row.get('Type', '')  # New field - rename to avoid conflict
                    tags_str = row.get('Tags', '')  # New Tags field
                    tags = [tag.strip() for tag in tags_str.split(';')] if tags_str and tags_str.strip() else []  # Parse semicolon-separated tags
                    image_filename = row.get('Image', '')  # New Image field
                    
                    # Skip empty rows
                    if not indicator_id or not time_period or not domain or not indicator_name:
                        continue
                    
                    # Parse stewards from semicolon-separated string
                    stewards_list = []
                    if steward_str and steward_str.strip():
                        stewards_list = [s.strip() for s in steward_str.split(';') if s.strip()]
                    
                    if not stewards_list:
                        continue  # Skip rows without stewards
                    
                    # Normalize "HL7" to "HL7 International" for consistency
                    stewards_list = ["HL7 International" if s == "HL7" else s for s in stewards_list]
                    
                    # First steward is the primary steward
                    primary_steward = stewards_list[0]
                    
                    # Track metadata
                    time_periods.add(time_period)
                    domains.add(domain)
                    stewards.update(stewards_list)
                    
                    # Parse values
                    value = None
                    if value_str and value_str.strip():
                        try:
                            # Handle percentage values
                            if value_str.endswith('%'):
                                value = float(value_str.rstrip('%'))
                            else:
                                value = float(value_str)
                        except ValueError:
                            # Skip invalid values
                            continue
                    
                    target = None
                    if target_str and target_str.strip():
                        try:
                            target = float(target_str)
                        except ValueError:
                            pass
                    
                    # Process image if provided (do this for every row, not just new indicators)
                    processed_image = None
                    if image_filename and image_filename.strip():
                        processed_image = self._copy_indicator_image(image_filename)
                    
                    # Create or update indicator
                    if indicator_id not in indicators:
                        # Use CSV values for unit and type, fallback to auto-determination if not provided
                        final_unit = unit if unit else self._determine_unit(indicator_type, indicator_name)
                        final_type = csv_type if csv_type else indicator_type
                        
                        # Use direction from CSV, fallback to auto-determination if not provided
                        direction = row.get('Direction', '').strip()
                        if direction:
                            trend_direction = direction
                        else:
                            trend_direction = self._determine_trend_direction(indicator_name, final_type)
                        
                        indicators[indicator_id] = KPIIndicator(
                            id=indicator_id,
                            name=indicator_name,
                            description=self._get_description(indicator_id, indicator_name),
                            domain=domain,
                            stewards=stewards_list,
                            primary_steward=primary_steward,
                            type=final_type,
                            unit=final_unit,
                            target=None,  # Legacy target - not used in new structure
                            targets=None,  # Annual targets - will be populated based on target_type
                            target_operation=None,  # Target operation - will be populated based on target_operation
                            tags=tags,  # Tags for categorization
                            image=None,  # Resolved after CSV scan from newest row with Image
                            trend_direction=trend_direction,  # Whether higher or lower values are better
                            measurements={}
                        )
                    else:
                        # Update existing indicator's stewards if needed
                        existing_stewards = set(indicators[indicator_id].stewards)
                        new_stewards = set(stewards_list)
                        if new_stewards != existing_stewards:
                            indicators[indicator_id].stewards = stewards_list
                            indicators[indicator_id].primary_steward = primary_steward
                    
                    if processed_image:
                        best_indicator_image[indicator_id] = self._indicator_image_best(
                            best_indicator_image.get(indicator_id), time_period, processed_image
                        )
                    
                    # Process notes - convert markdown to HTML if present
                    processed_notes = None
                    if notes and notes.strip():
                        processed_notes = self._convert_markdown_to_html(notes)
                    
                    # Create measurement for this time period
                    measurement = KPIMeasurement(
                        value=value,
                        target=None,  # Will be set based on target_type
                        notes=processed_notes
                    )
                    
                    # Handle targets based on target_type
                    if target is not None:
                        if target_type == 'period':
                            # Period-specific target - set on the measurement
                            measurement.target = target
                        elif target_type == 'annual':
                            # Annual target - add to the indicator's targets dict
                            year = time_period.split('-')[0] if '-' in time_period else time_period
                            if indicators[indicator_id].targets is None:
                                indicators[indicator_id].targets = {}
                            indicators[indicator_id].targets[year] = target
                            # Set target operation for annual targets
                            if target_operation in ['sum', 'average']:
                                indicators[indicator_id].target_operation = target_operation
                            # Don't set measurement.target for annual targets
                        else:
                            # No target_type specified - assume period target for backward compatibility
                            measurement.target = target
                    
                    indicators[indicator_id].measurements[time_period] = measurement
        except UnicodeDecodeError as e:
            # If UTF-8 fails, try with latin-1 encoding (which can read any byte)
            print(f"Warning: UTF-8 decode error, trying latin-1: {e}")
            with open(self.csv_path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    indicator_id = row['ID']
                    time_period = row['Time Period']
                    domain = row['Domain']
                    indicator_name = row['Indicator']
                    indicator_type = row['Type']
                    value_str = row['Value']
                    notes = row['Notes'] if row['Notes'] else None
                    steward_str = row['Steward']
                    target_str = row['Target']
                    target_type = row.get('Target Type', '').lower()
                    target_operation = row.get('Target Operation', '').lower() if row.get('Target Operation') else ''
                    unit = row.get('Unit', '')
                    csv_type = row.get('Type', '')
                    tags_str = row.get('Tags', '')
                    tags = [tag.strip() for tag in tags_str.split(';')] if tags_str and tags_str.strip() else []
                    image_filename = row.get('Image', '')
                    
                    # Skip empty rows
                    if not indicator_id or not time_period or not domain or not indicator_name:
                        continue
                    
                    # Parse stewards from semicolon-separated string
                    stewards_list = []
                    if steward_str and steward_str.strip():
                        stewards_list = [s.strip() for s in steward_str.split(';') if s.strip()]
                    
                    if not stewards_list:
                        continue
                    
                    # Normalize "HL7" to "HL7 International" for consistency
                    stewards_list = ["HL7 International" if s == "HL7" else s for s in stewards_list]
                    
                    primary_steward = stewards_list[0]
                    
                    # Track metadata
                    time_periods.add(time_period)
                    domains.add(domain)
                    stewards.update(stewards_list)
                    
                    # Parse values
                    value = None
                    if value_str and value_str.strip():
                        try:
                            if value_str.endswith('%'):
                                value = float(value_str.rstrip('%'))
                            else:
                                value = float(value_str)
                        except ValueError:
                            continue
                    
                    target = None
                    if target_str and target_str.strip():
                        try:
                            target = float(target_str)
                        except ValueError:
                            pass
                    
                    # Process image if provided
                    processed_image = None
                    if image_filename and image_filename.strip():
                        processed_image = self._copy_indicator_image(image_filename)
                    
                    # Create or update indicator
                    if indicator_id not in indicators:
                        final_unit = unit if unit else self._determine_unit(indicator_type, indicator_name)
                        final_type = csv_type if csv_type else indicator_type
                        
                        direction = row.get('Direction', '').strip()
                        if direction:
                            trend_direction = direction
                        else:
                            trend_direction = self._determine_trend_direction(indicator_name, final_type)
                        
                        indicators[indicator_id] = KPIIndicator(
                            id=indicator_id,
                            name=indicator_name,
                            description=self._get_description(indicator_id, indicator_name),
                            domain=domain,
                            stewards=stewards_list,
                            primary_steward=primary_steward,
                            type=final_type,
                            unit=final_unit,
                            target=None,
                            targets=None,
                            target_operation=None,
                            tags=tags,
                            image=None,
                            trend_direction=trend_direction,
                            measurements={}
                        )
                    else:
                        existing_stewards = set(indicators[indicator_id].stewards)
                        new_stewards = set(stewards_list)
                        if new_stewards != existing_stewards:
                            indicators[indicator_id].stewards = stewards_list
                            indicators[indicator_id].primary_steward = primary_steward
                    
                    if processed_image:
                        best_indicator_image[indicator_id] = self._indicator_image_best(
                            best_indicator_image.get(indicator_id), time_period, processed_image
                        )
                    
                    # Process notes - convert markdown to HTML if present
                    processed_notes = None
                    if notes and notes.strip():
                        processed_notes = self._convert_markdown_to_html(notes)
                    
                    # Create measurement for this time period
                    measurement = KPIMeasurement(
                        value=value,
                        target=None,
                        notes=processed_notes
                    )
                    
                    # Handle targets based on target_type
                    if target is not None:
                        if target_type == 'period':
                            measurement.target = target
                        elif target_type == 'annual':
                            year = time_period.split('-')[0] if '-' in time_period else time_period
                            if indicators[indicator_id].targets is None:
                                indicators[indicator_id].targets = {}
                            indicators[indicator_id].targets[year] = target
                            if target_operation in ['sum', 'average']:
                                indicators[indicator_id].target_operation = target_operation
                        else:
                            measurement.target = target
                    
                    indicators[indicator_id].measurements[time_period] = measurement
        
        for ind_id, (_, img_file) in best_indicator_image.items():
            if ind_id in indicators:
                indicators[ind_id].image = img_file
        
        # Sort stewards with HL7/HL7 International first, then alphabetically
        stewards_list = list(stewards)
        hl7_steward = None
        if "HL7 International" in stewards_list:
            hl7_steward = "HL7 International"
        elif "HL7" in stewards_list:
            hl7_steward = "HL7"
        
        if hl7_steward:
            stewards_list.remove(hl7_steward)
            stewards_list.sort()
            stewards_list.insert(0, hl7_steward)
        else:
            stewards_list.sort()
        
        # Create metadata
        current_time = datetime.now()
        metadata = KPIMetadata(
            version="1.0",
            last_updated=current_time.strftime("%Y-%m-%d"),
            data_source="HL7 KPI Dashboard - CSV Import",
            time_periods=sorted(list(time_periods)),
            domains=sorted(list(domains)),
            stewards=stewards_list,
            refresh_timestamp=int(current_time.timestamp())
        )
        
        return KPIData(
            metadata=metadata,
            indicators=indicators
        )
    
    def populate_indicators(self, dry_run: bool = False) -> Dict[str, Any]:
        """Populate indicators 27, 28, 47, 48 from published standards CSV
        
        Args:
            dry_run: If True, return what would be updated without actually updating
            
        Returns:
            Dictionary with update statistics and details
        """
        return self._populate_published_specs_indicators(dry_run=dry_run)
    
    def save_json(self, output_path: str = "data/processed/kpi_data.json", populate_indicators: bool = False):
        """Convert and save to JSON file
        
        Args:
            output_path: Path to save the JSON file
            populate_indicators: If True, populate indicators 27, 28, 47, 48 before conversion
        """
        # Optionally populate indicators from published standards CSV before conversion
        if populate_indicators:
            self._populate_published_specs_indicators(dry_run=False)
        
        # Convert the CSV to JSON
        kpi_data = self.convert()
        
        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(kpi_data.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted CSV to JSON: {output_path}")
        print(f"Generated {len(kpi_data.indicators)} indicators")
        print(f"Time periods: {kpi_data.metadata.time_periods}")
        print(f"Domains: {kpi_data.metadata.domains}")
        print(f"Stewards: {kpi_data.metadata.stewards}")
        
        return output_path

def main():
    """Main function to run the converter"""
    converter = CSVToJSONConverter()
    converter.save_json()

if __name__ == "__main__":
    main() 