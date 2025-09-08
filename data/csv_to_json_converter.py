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
from typing import Dict, List, Optional, Any
from datetime import datetime
import markdown

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.models import KPIData, KPIMetadata, KPIIndicator, KPIMeasurement

class CSVToJSONConverter:
    def __init__(self, csv_path: str = "data/raw/all_kpis.csv", 
                 definitions_path: str = "data/raw/indicator-definitions.csv"):
        self.csv_path = Path(csv_path)
        self.definitions_path = Path(definitions_path)
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
    
    def convert(self) -> KPIData:
        """Convert CSV data to JSON structure"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        indicators = {}
        time_periods = set()
        domains = set()
        stewards = set()
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
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
                        image=processed_image,  # Optional image filename
                        measurements={}
                    )
                else:
                    # Update existing indicator's stewards if needed
                    existing_stewards = set(indicators[indicator_id].stewards)
                    new_stewards = set(stewards_list)
                    if new_stewards != existing_stewards:
                        indicators[indicator_id].stewards = stewards_list
                        indicators[indicator_id].primary_steward = primary_steward
                    
                    # Update image if provided
                    if processed_image:
                        indicators[indicator_id].image = processed_image
                
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
    
    def save_json(self, output_path: str = "data/processed/kpi_data.json"):
        """Convert and save to JSON file"""
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