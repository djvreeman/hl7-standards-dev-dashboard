import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

class PublishedStandardsService:
    def __init__(self, csv_path: str = "data/raw/HL7 Standards Tracking - Stats Metrics - Published Specifications.csv"):
        self.csv_path = Path(csv_path)
        self._data_cache = None
    
    def _load_data(self) -> Dict[int, List[Dict[str, Any]]]:
        """Load and parse CSV data, organizing by year"""
        if self._data_cache is not None:
            return self._data_cache
        
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        standards_by_year = defaultdict(list)
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Only include publications (exclude Reaffirmations)
                pub_status = row.get('Pub Status', '').strip()
                if pub_status != 'Publication':
                    continue
                
                # Extract year from Date field
                date_str = row.get('Date', '').strip()
                if not date_str:
                    # Fallback to FY if Date is empty
                    fy_str = row.get('FY', '').strip()
                    if fy_str:
                        try:
                            year = int(fy_str)
                        except ValueError:
                            continue
                    else:
                        continue
                else:
                    # Parse date string (format: "1/10/2019" or "M/D/YYYY")
                    try:
                        # Try parsing as M/D/YYYY
                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                        year = date_obj.year
                    except ValueError:
                        # Try parsing as M/D/YY
                        try:
                            date_obj = datetime.strptime(date_str, '%m/%d/%y')
                            year = date_obj.year
                        except ValueError:
                            # Fallback to FY
                            fy_str = row.get('FY', '').strip()
                            if fy_str:
                                try:
                                    year = int(fy_str)
                                except ValueError:
                                    continue
                            else:
                                continue
                
                # Get specification name (prefer clean name, fallback to full name)
                spec_name = row.get('Specification Clean Name', '').strip()
                if not spec_name:
                    spec_name = row.get('Specification', '').strip()
                
                if not spec_name:
                    continue
                
                # Extract additional metadata
                family = row.get('Family', '').strip()
                realm = row.get('Realm', '').strip()
                accelerator = row.get('Accelerator', '').strip()
                
                standard_data = {
                    'name': spec_name,
                    'family': family,
                    'realm': realm,
                    'accelerator': accelerator,
                    'date': date_str,
                    'pub_status': pub_status
                }
                
                standards_by_year[year].append(standard_data)
        
        # Sort standards within each year by date
        for year in standards_by_year:
            standards_by_year[year].sort(key=lambda x: self._parse_date_for_sort(x['date']))
        
        self._data_cache = dict(standards_by_year)
        return self._data_cache
    
    def _parse_date_for_sort(self, date_str: str) -> datetime:
        """Parse date string for sorting purposes"""
        if not date_str:
            return datetime.min
        
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%m/%d/%y')
            except ValueError:
                return datetime.min
    
    def get_standards_for_year(self, year: int) -> List[Dict[str, Any]]:
        """Get all published standards for a specific year"""
        data = self._load_data()
        return data.get(year, [])
    
    def get_available_years(self) -> List[int]:
        """Get list of all available years"""
        data = self._load_data()
        return sorted(data.keys())
    
    def get_years_range(self) -> Dict[str, int]:
        """Get the range of available years"""
        years = self.get_available_years()
        if not years:
            return {'min': None, 'max': None}
        return {'min': min(years), 'max': max(years)}
    
    def refresh_data(self):
        """Clear cache and reload data"""
        self._data_cache = None
        self._load_data()
