import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
import logging
from app.models import GeographicFinancialMetrics, GeographicYearData, CountryRevenueData
from app.country_normalizer import get_country_normalizer

logger = logging.getLogger(__name__)

class GeographicFinancialParser:
    """Parser for geographic financial data from Excel files"""
    
    def __init__(self, excel_path: str = "data/draft/member-affiliate-revenue-draft-2025.xlsx"):
        self.excel_path = Path(excel_path)
        self.country_normalizer = get_country_normalizer()
    
    def parse_excel(self) -> GeographicFinancialMetrics:
        """Parse the Excel file and return geographic financial metrics"""
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")
        
        # Read both sheets
        xls = pd.ExcelFile(self.excel_path)
        
        # Parse member revenue sheet
        member_df = pd.read_excel(xls, sheet_name=0, header=None)
        member_data = self._parse_member_revenue_sheet(member_df)
        
        # Parse affiliate revenue sheet
        affiliate_df = pd.read_excel(xls, sheet_name=1, header=None)
        affiliate_data = self._parse_affiliate_revenue_sheet(affiliate_df)
        
        # Combine data by year
        years_data = {}
        all_years = set(member_data.keys()) | set(affiliate_data.keys())
        
        for year in all_years:
            member_revenue_by_country = member_data.get(year, {})
            affiliate_revenue_by_country = affiliate_data.get(year, {})
            
            # Get all unique countries
            all_countries = set(member_revenue_by_country.keys()) | set(affiliate_revenue_by_country.keys())
            
            countries = {}
            for country in all_countries:
                membership_rev = member_revenue_by_country.get(country, 0.0)
                affiliate_rev = affiliate_revenue_by_country.get(country, 0.0)
                
                countries[country] = CountryRevenueData(
                    country=country,
                    membership_revenue=float(membership_rev) if membership_rev else 0.0,
                    affiliate_revenue=float(affiliate_rev) if affiliate_rev else 0.0
                )
            
            years_data[year] = GeographicYearData(
                year=year,
                countries=countries
            )
        
        years_list = [years_data[y] for y in sorted(years_data.keys())]
        years_available = sorted(years_data.keys())
        latest_year = max(years_available) if years_available else 2025
        
        return GeographicFinancialMetrics(
            years=years_list,
            years_available=years_available,
            latest_year=latest_year
        )
    
    def _parse_member_revenue_sheet(self, df: pd.DataFrame) -> Dict[int, Dict[str, float]]:
        """Parse the member revenue sheet"""
        # The sheet structure is:
        # Column 0: Revenue values
        # Column 1: Country names
        # No header row - all rows are data
        
        # Extract year from filename (default to 2025)
        year = 2025
        if '2025' in str(self.excel_path):
            year = 2025
        elif '2024' in str(self.excel_path):
            year = 2024
        elif '2023' in str(self.excel_path):
            year = 2023
        
        member_revenue = {}
        
        # Parse all rows as data
        for idx in range(len(df)):
            row = df.iloc[idx]
            # Column 0 is revenue, column 1 is country
            revenue_val = row.iloc[0]
            country = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) and len(row) > 1 else None
            
            # Skip if country is missing or invalid
            if not country or country.lower() == 'nan' or country == '':
                continue
            
            # Check if revenue value is valid (numeric)
            if pd.notna(revenue_val):
                try:
                    revenue = float(revenue_val)
                    # Normalize country name to World Bank standard
                    country = self.country_normalizer.normalize(country)
                    if country not in member_revenue:
                        member_revenue[country] = 0.0
                    member_revenue[country] += revenue
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse revenue value '{revenue_val}' for country '{country}'")
        
        return {year: member_revenue}
    
    def _parse_affiliate_revenue_sheet(self, df: pd.DataFrame) -> Dict[int, Dict[str, float]]:
        """Parse the affiliate revenue sheet"""
        # The sheet structure is:
        # Column 0: Country names
        # Column 1: Revenue values
        # First row is typically a header (e.g., "Australia", "15030")
        
        # Extract year from filename (default to 2025)
        year = 2025
        if '2025' in str(self.excel_path):
            year = 2025
        elif '2024' in str(self.excel_path):
            year = 2024
        elif '2023' in str(self.excel_path):
            year = 2023
        
        affiliate_revenue = {}
        
        # Check if first row is a header by checking if the country name looks like a header
        # Headers are typically single words or look like column labels
        start_row = 0
        if len(df) > 0:
            first_country = str(df.iloc[0, 0]).strip() if pd.notna(df.iloc[0, 0]) else ""
            first_revenue_val = df.iloc[0, 1] if len(df.columns) > 1 else None
            
            # If first row has a country name that looks like a header (e.g., "Australia" as column name)
            # and the revenue value is numeric but very large (like a year), skip it
            # Or if the country name matches common header patterns
            if first_country and len(df) > 1:
                # Check if second row's country looks more like actual data
                second_country = str(df.iloc[1, 0]).strip() if len(df) > 1 and pd.notna(df.iloc[1, 0]) else ""
                # If first row country is a single common word that could be a header, skip it
                header_indicators = ['country', 'nation', 'australia', 'canada']  # Common header-like values
                if first_country.lower() in header_indicators or (
                    pd.notna(first_revenue_val) and 
                    isinstance(first_revenue_val, (int, float)) and 
                    first_revenue_val > 10000  # Large number might be a year/header
                ):
                    start_row = 1
        
        for idx in range(start_row, len(df)):
            row = df.iloc[idx]
            country = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            revenue_val = row.iloc[1] if len(row) > 1 else None
            
            # Skip if country is missing or invalid
            if not country or country.lower() == 'nan' or country == '':
                continue
            
            if pd.notna(revenue_val):
                try:
                    revenue = float(revenue_val)
                    # Normalize country name to World Bank standard
                    country = self.country_normalizer.normalize(country)
                    if country not in affiliate_revenue:
                        affiliate_revenue[country] = 0.0
                    affiliate_revenue[country] += revenue
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse revenue value '{revenue_val}' for country '{country}'")
        
        return {year: affiliate_revenue}
    
    def _extract_year_from_value(self, value: str) -> Optional[int]:
        """Try to extract a year from a value"""
        if not value:
            return None
        
        value_str = str(value).strip()
        
        # Check if it's a 4-digit year
        if value_str.isdigit() and len(value_str) == 4:
            year = int(value_str)
            if 2000 <= year <= 2100:
                return year
        
        # Check if it's a year like "1545" (might be 2015 or 2025)
        if value_str.isdigit():
            year = int(value_str)
            # If it's a 4-digit number that looks like a year typo
            if 1500 <= year < 2000:
                # Assume it's meant to be 2000+
                return 2000 + (year % 100)
            elif 2000 <= year <= 2100:
                return year
        
        return None
    
    def _is_header_row(self, row: pd.Series) -> bool:
        """Check if a row looks like a header row"""
        # If first value is a country name or non-numeric, it's likely a header
        first_val = str(row.iloc[0]) if len(row) > 0 else ""
        return not first_val.replace('.', '').replace('-', '').isdigit()
    
    def parse_file_intelligent(self, file_path: Path, revenue_type: str, year: int) -> tuple[Dict[str, float], List[str]]:
        """
        Intelligently parse a CSV or Excel file to extract country revenue data
        
        Args:
            file_path: Path to the CSV or Excel file
            revenue_type: 'membership' or 'affiliate'
            year: Year for the data
            
        Returns:
            Tuple of (dictionary mapping country names to revenue values, list of unmatched country names)
        """
        # Detect file type
        file_ext = file_path.suffix.lower()
        
        # Read file
        if file_ext == '.csv':
            # Try different encodings and separators for CSV
            try:
                df = pd.read_csv(file_path, header=None, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file_path, header=None, encoding='latin-1')
                except:
                    df = pd.read_csv(file_path, header=None, encoding='cp1252')
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, header=None)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported types: .csv, .xlsx, .xls")
        
        if df.empty:
            raise ValueError("File is empty")
        
        # Detect which column has country names and which has dollar values
        country_col_idx, revenue_col_idx = self._detect_columns(df)
        
        if country_col_idx is None or revenue_col_idx is None:
            raise ValueError("Could not detect country and revenue columns. Please ensure the file has country names and dollar values.")
        
        # Parse data
        revenue_by_country = {}
        unmatched_countries = []
        original_to_normalized = {}  # Track original names for unmatched detection
        
        # Skip header rows - check first few rows to find where data starts
        start_row = 0
        for check_idx in range(min(3, len(df))):
            row = df.iloc[check_idx]
            country_val = str(row.iloc[country_col_idx]).strip() if pd.notna(row.iloc[country_col_idx]) else ''
            revenue_val = row.iloc[revenue_col_idx] if len(row) > revenue_col_idx else None
            
            # If this looks like a header row, skip it
            if country_val.lower() in ['country', 'nation', 'name', 'location', ''] or \
               (pd.notna(revenue_val) and not self._looks_like_revenue(str(revenue_val))):
                start_row = check_idx + 1
            else:
                break
        
        for idx in range(start_row, len(df)):
            row = df.iloc[idx]
            
            # Get country name
            country_raw = str(row.iloc[country_col_idx]).strip() if pd.notna(row.iloc[country_col_idx]) else None
            if not country_raw or country_raw.lower() in ['nan', '', 'country', 'nation', 'total', 'sum', 'header']:
                continue
            
            # Get revenue value
            revenue_raw = row.iloc[revenue_col_idx] if len(row) > revenue_col_idx else None
            if pd.isna(revenue_raw):
                continue
            
            # Parse revenue value (handle currency formatting)
            try:
                revenue = self._parse_revenue_value(revenue_raw)
                if revenue is None or revenue <= 0:
                    continue
            except (ValueError, TypeError):
                logger.warning(f"Could not parse revenue value '{revenue_raw}' for country '{country_raw}'")
                continue
            
            # Normalize country name for comparison (remove extra spaces, handle variations)
            country_normalized_lower = country_raw.lower().strip()
            
            # Special handling for "Central America" - normalize to "Central America and Dominican Republic"
            # Handle variations like "Central America", "CentralAmerica", etc.
            if country_normalized_lower == 'central america' or country_normalized_lower.replace(' ', '') == 'centralamerica':
                country_normalized = 'Central America and Dominican Republic'
                was_matched = True  # This is a special case, not an unmatched country
            # Special handling for "Taiwan" - normalize to "Taiwan, China"
            # Handle variations like "Taiwan", "Taiwan Province", etc.
            elif country_normalized_lower == 'taiwan' or country_normalized_lower.startswith('taiwan'):
                country_normalized = 'Taiwan, China'
                was_matched = True  # This is a special case, not an unmatched country
            # Special handling for "Other" affiliate category
            # Handle variations like "Other", "INTERNATIONAL AFFILIATES", "International Affiliates", etc.
            elif (country_normalized_lower == 'other' or 
                  country_normalized_lower == 'international affiliates' or
                  country_normalized_lower == 'international affiliate' or
                  'international affiliates' in country_normalized_lower):
                country_normalized = 'Other (International Affiliates)'
                was_matched = True  # This is a special case, not an unmatched country
            else:
                # Normalize country name
                country_normalized = self.country_normalizer.normalize(country_raw)
                
                # Check if the country was matched to a World Bank standard name
                # If normalized name equals original (case-insensitive), it likely wasn't matched
                # Also check if normalized name is in the World Bank cache
                normalized_lower = country_normalized.lower()
                original_lower = country_raw.lower()
                
                # Check if normalized name exists in World Bank cache (as a value, not just a key)
                wb_standard_names = {v.lower() for v in self.country_normalizer._country_cache.values() if v}
                was_matched = normalized_lower in wb_standard_names or normalized_lower != original_lower
                
                # If country wasn't matched to a World Bank standard, flag it
                if not was_matched:
                    if country_raw not in unmatched_countries:
                        unmatched_countries.append(country_raw)
            
            # Aggregate by country (in case of duplicates)
            if country_normalized not in revenue_by_country:
                revenue_by_country[country_normalized] = 0.0
            revenue_by_country[country_normalized] += revenue
            
            # Log special cases for debugging
            if country_normalized in ['Taiwan, China', 'Central America and Dominican Republic', 'Other (International Affiliates)']:
                logger.info(f"Special case: '{country_raw}' -> '{country_normalized}' with revenue {revenue}")
        
        return revenue_by_country, unmatched_countries
    
    def _detect_columns(self, df: pd.DataFrame) -> tuple:
        """
        Intelligently detect which column contains country names and which contains revenue values
        
        Returns:
            Tuple of (country_column_index, revenue_column_index) or (None, None) if not detected
        """
        if df.empty or len(df.columns) < 2:
            return None, None
        
        # Analyze first few rows to detect patterns
        sample_size = min(20, len(df))
        sample_df = df.head(sample_size)
        
        country_scores = {}
        revenue_scores = {}
        
        for col_idx in range(len(df.columns)):
            country_score = 0
            revenue_score = 0
            
            for row_idx in range(sample_size):
                value = sample_df.iloc[row_idx, col_idx]
                
                if pd.isna(value):
                    continue
                
                value_str = str(value).strip()
                
                # Check if it looks like a country name
                if self._looks_like_country_name(value_str):
                    country_score += 1
                
                # Check if it looks like a revenue value
                if self._looks_like_revenue(value_str):
                    revenue_score += 1
            
            country_scores[col_idx] = country_score
            revenue_scores[col_idx] = revenue_score
        
        # Find best matches
        best_country_col = max(country_scores.items(), key=lambda x: x[1]) if country_scores else None
        best_revenue_col = max(revenue_scores.items(), key=lambda x: x[1]) if revenue_scores else None
        
        # Require minimum confidence (at least 3 matches in sample)
        country_col_idx = best_country_col[0] if best_country_col and best_country_col[1] >= 3 else None
        revenue_col_idx = best_revenue_col[0] if best_revenue_col and best_revenue_col[1] >= 3 else None
        
        # If we couldn't detect, try common patterns
        if country_col_idx is None or revenue_col_idx is None:
            # Try all column pairs to find the best match
            best_match_score = 0
            best_country_idx = None
            best_revenue_idx = None
            
            for i in range(len(df.columns)):
                for j in range(len(df.columns)):
                    if i == j:
                        continue
                    
                    # Score this pair
                    country_matches = sum(1 for row_idx in range(min(10, len(df))) 
                                         if self._looks_like_country_name(str(df.iloc[row_idx, i])))
                    revenue_matches = sum(1 for row_idx in range(min(10, len(df))) 
                                         if self._looks_like_revenue(str(df.iloc[row_idx, j])))
                    
                    match_score = country_matches + revenue_matches
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_country_idx = i
                        best_revenue_idx = j
            
            # Use best match if it has reasonable confidence
            if best_match_score >= 6:  # At least 6 matches out of 10 rows
                country_col_idx = best_country_idx
                revenue_col_idx = best_revenue_idx
        
        return country_col_idx, revenue_col_idx
    
    def _looks_like_country_name(self, value: str) -> bool:
        """Check if a value looks like a country name"""
        if not value or len(value) < 2:
            return False
        
        value_lower = value.lower()
        
        # Common non-country patterns
        if value_lower in ['country', 'nation', 'total', 'sum', 'header', 'name', '']:
            return False
        
        # Check if it's mostly letters (country names are typically text)
        if not value.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            return False
        
        # Check if it's not a number
        try:
            float(value.replace(',', '').replace('$', '').replace('(', '').replace(')', ''))
            return False
        except ValueError:
            pass
        
        # Check length (country names are typically 2-50 characters)
        if len(value) < 2 or len(value) > 50:
            return False
        
        return True
    
    def _looks_like_revenue(self, value: str) -> bool:
        """Check if a value looks like a revenue/dollar amount"""
        if not value:
            return False
        
        value_str = str(value).strip()
        
        # Remove common currency symbols and formatting
        cleaned = value_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
        # Try to parse as number
        try:
            num_value = float(cleaned)
            # Revenue values are typically positive and reasonable (not too small, not astronomical)
            if num_value > 0 and num_value < 1e12:  # Less than 1 trillion
                return True
        except ValueError:
            pass
        
        # Check for currency patterns
        if '$' in value_str or ',' in value_str:
            # Has currency formatting
            try:
                cleaned_num = float(cleaned)
                if cleaned_num > 0:
                    return True
            except ValueError:
                pass
        
        return False
    
    def _parse_revenue_value(self, value) -> Optional[float]:
        """Parse a revenue value from various formats"""
        if pd.isna(value):
            return None
        
        value_str = str(value).strip()
        
        # Remove currency symbols and formatting
        cleaned = value_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
        try:
            return float(cleaned)
        except ValueError:
            return None

