import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from app.models import GeographicFinancialMetrics, GeographicYearData, CountryRevenueData
from app.geographic_financial_parser import GeographicFinancialParser
from app.country_normalizer import get_country_normalizer

logger = logging.getLogger(__name__)

class GeographicFinancialService:
    """Service for managing geographic financial data"""
    
    def __init__(self, 
                 excel_path: str = "data/draft/member-affiliate-revenue-draft-2025.xlsx",
                 cache_file: str = "data/processed/geographic_financial_data.json"):
        self.excel_path = excel_path
        self.cache_file = Path(cache_file)
        self.parser = GeographicFinancialParser(excel_path)
        self._cached_data = None
        self.country_normalizer = get_country_normalizer()
    
    def get_geographic_metrics(self) -> GeographicFinancialMetrics:
        """Get geographic financial metrics, using cache if available"""
        if self._cached_data is None:
            self._load_financial_data()
        return self._cached_data
    
    def _load_financial_data(self):
        """Load geographic financial data from cache or parse Excel file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data_dict = json.load(f)
                self._cached_data = GeographicFinancialMetrics(**data_dict)
                return
            except Exception as e:
                logger.warning(f"Error loading cached geographic financial data: {e}")
        
        # Parse Excel file if cache doesn't exist or is invalid
        self._cached_data = self.parser.parse_excel()
        self._save_financial_data()
    
    def _save_financial_data(self):
        """Save geographic financial data to cache file"""
        if self._cached_data:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self._cached_data.dict(), f, indent=2)
    
    def refresh_financial_data(self):
        """Refresh geographic financial data by re-parsing Excel file"""
        self._cached_data = None
        if self.cache_file.exists():
            self.cache_file.unlink()
        self._load_financial_data()
    
    def get_key_indicators(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Get key indicators for a specific year (or latest year) with trend data"""
        if self._cached_data is None:
            self._load_financial_data()
        
        if year:
            year_data = self._cached_data.get_year(year)
        else:
            year_data = self._cached_data.get_latest_data()
        
        if not year_data:
            return {
                "total_revenue": 0.0,
                "total_membership_revenue": 0.0,
                "non_us_membership_revenue": 0.0,
                "non_us_membership_revenue_pct": 0.0,
                "affiliate_revenue": 0.0,
                "trends": {}
            }
        
        current_year = year_data.year
        total_membership = year_data.total_membership_revenue
        non_us_membership = year_data.non_us_membership_revenue
        non_us_membership_pct = (non_us_membership / total_membership * 100) if total_membership > 0 else 0.0
        total_revenue = year_data.total_revenue
        affiliate_revenue = year_data.total_affiliate_revenue
        
        # Calculate trends by comparing with previous year
        trends = {}
        previous_year_data = self._cached_data.get_year(current_year - 1) if current_year > 0 else None
        
        def calculate_trend(current_val: float, previous_val: Optional[float]) -> Optional[Dict[str, Any]]:
            """Calculate trend data for a value"""
            if previous_val is None:
                return None
            
            if previous_val == 0:
                change_pct = 100.0 if current_val > 0 else 0.0
            else:
                change_pct = ((current_val - previous_val) / previous_val) * 100
            
            # Determine trend direction (for revenue, higher is better = up)
            if abs(change_pct) < 0.01:  # Essentially no change
                trend = "stable"
            elif change_pct > 0:
                trend = "up"
            else:
                trend = "down"
            
            return {
                "previous": previous_val,
                "change_pct": change_pct,
                "trend": trend
            }
        
        if previous_year_data:
            trends["total_revenue"] = calculate_trend(total_revenue, previous_year_data.total_revenue)
            trends["total_membership_revenue"] = calculate_trend(total_membership, previous_year_data.total_membership_revenue)
            trends["non_us_membership_revenue"] = calculate_trend(non_us_membership, previous_year_data.non_us_membership_revenue)
            trends["affiliate_revenue"] = calculate_trend(affiliate_revenue, previous_year_data.total_affiliate_revenue)
            
            # For percentage, calculate trend based on the percentage values
            prev_total_membership = previous_year_data.total_membership_revenue
            prev_non_us_membership = previous_year_data.non_us_membership_revenue
            prev_non_us_pct = (prev_non_us_membership / prev_total_membership * 100) if prev_total_membership > 0 else 0.0
            trends["non_us_membership_revenue_pct"] = calculate_trend(non_us_membership_pct, prev_non_us_pct)
        
        return {
            "total_revenue": total_revenue,
            "total_membership_revenue": total_membership,
            "non_us_membership_revenue": non_us_membership,
            "non_us_membership_revenue_pct": non_us_membership_pct,
            "affiliate_revenue": affiliate_revenue,
            "trends": trends,
            "current_year": current_year,
            "previous_year": current_year - 1 if previous_year_data else None
        }
    
    def get_country_data_for_map(self, year: Optional[int] = None, data_type: str = "combined") -> Dict[str, float]:
        """
        Get country data formatted for map visualization
        
        Args:
            year: Year to get data for (None for latest)
            data_type: "membership", "affiliate", or "combined"
        
        Returns:
            Dictionary mapping country names to revenue values
            Note: Excludes "Other (International Affiliates)" as it's not mappable
        """
        if year:
            year_data = self._cached_data.get_year(year)
        else:
            year_data = self._cached_data.get_latest_data()
        
        if not year_data:
            return {}
        
        result = {}
        for country, country_data in year_data.countries.items():
            # Skip "Other" category - it's not mappable
            if country == 'Other (International Affiliates)':
                continue
                
            if data_type == "membership":
                result[country] = country_data.membership_revenue
            elif data_type == "affiliate":
                result[country] = country_data.affiliate_revenue
            else:  # combined
                result[country] = country_data.total_revenue
        
        return result
    
    def get_country_code_mapping(self) -> Dict[str, str]:
        """Get mapping from country names to ISO country codes for map visualization"""
        # Common country name to ISO code mappings
        # This is a simplified mapping - you may want to use a library like pycountry for more complete coverage
        return {
            "United States": "US",
            "United Kingdom": "GB",
            "Canada": "CA",
            "Australia": "AU",
            "Germany": "DE",
            "France": "FR",
            "Japan": "JP",
            "Netherlands": "NL",
            "Switzerland": "CH",
            "India": "IN",
            "Brazil": "BR",
            "China": "CN",
            "South Korea": "KR",
            "Korea": "KR",
            "Spain": "ES",
            "Italy": "IT",
            "Poland": "PL",
            "Sweden": "SE",
            "Norway": "NO",
            "Denmark": "DK",
            "Finland": "FI",
            "Belgium": "BE",
            "Austria": "AT",
            "Portugal": "PT",
            "Greece": "GR",
            "Ireland": "IE",
            "New Zealand": "NZ",
            "Singapore": "SG",
            "Taiwan": "TW",
            "Hong Kong": "HK",
            "Malaysia": "MY",
            "Thailand": "TH",
            "Philippines": "PH",
            "Indonesia": "ID",
            "South Africa": "ZA",
            "Mexico": "MX",
            "Argentina": "AR",
            "Chile": "CL",
            "Colombia": "CO",
            "Peru": "PE",
            "Ecuador": "EC",
            "Costa Rica": "CR",
            "Bulgaria": "BG",
            "Croatia": "HR",
            "Estonia": "EE",
            "Luxembourg": "LU",
            "Malta": "MT",
            "Montenegro": "ME",
            "Romania": "RO",
            "Slovenia": "SI",
            "Slovak Republic": "SK",
            "Czech Republic": "CZ",
            "Russia": "RU",
            "Ukraine": "UA",
            "Saudi Arabia": "SA",
            "UAE": "AE",
            "Central America": None,  # Not a single country
        }
    
    def get_countries_for_year(self, year: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        """
        Get all countries with their revenue data for a specific year
        
        Args:
            year: Year to get data for (None for latest)
            
        Returns:
            Dictionary mapping country names to their revenue data
            Format: {country_name: {"membership_revenue": float, "affiliate_revenue": float}}
        """
        if self._cached_data is None:
            self._load_financial_data()
        
        if year:
            year_data = self._cached_data.get_year(year)
        else:
            year_data = self._cached_data.get_latest_data()
        
        if not year_data:
            return {}
        
        result = {}
        for country, country_data in year_data.countries.items():
            result[country] = {
                "membership_revenue": country_data.membership_revenue,
                "affiliate_revenue": country_data.affiliate_revenue
            }
        
        return result
    
    def update_country_revenue(self, year: int, country: str, 
                              membership_revenue: Optional[float] = None,
                              affiliate_revenue: Optional[float] = None) -> Dict[str, Any]:
        """
        Update revenue for a country in a specific year
        
        Args:
            year: Year to update
            country: Country name (will be normalized)
            membership_revenue: New membership revenue (None to keep existing)
            affiliate_revenue: New affiliate revenue (None to keep existing)
            
        Returns:
            Updated country data
        """
        if self._cached_data is None:
            self._load_financial_data()
        
        # Normalize country name
        normalized_country = self.country_normalizer.normalize(country)
        
        # Get or create year data
        year_data = self._cached_data.get_year(year)
        if not year_data:
            # Create new year data
            year_data = GeographicYearData(year=year, countries={})
            self._cached_data.years.append(year_data)
            self._cached_data.years.sort(key=lambda y: y.year)
            self._cached_data.years_available = sorted([y.year for y in self._cached_data.years])
            if year > self._cached_data.latest_year:
                self._cached_data.latest_year = year
        
        # Handle special cases where old entries might exist with different names
        # For example, "Taiwan" should be migrated to "Taiwan, China"
        old_name_mappings = {
            'Taiwan': 'Taiwan, China',
            'Central America': 'Central America and Dominican Republic',
            'Other': 'Other (International Affiliates)',
            'INTERNATIONAL AFFILIATES': 'Other (International Affiliates)',
            'International Affiliates': 'Other (International Affiliates)',
            'International Affiliate': 'Other (International Affiliates)'
        }
        
        # Check if there's an old entry that should be migrated
        old_name = None
        for old, new in old_name_mappings.items():
            if normalized_country == new and old in year_data.countries:
                old_name = old
                break
        
        # If we found an old entry, merge it into the normalized entry
        if old_name and old_name in year_data.countries:
            old_data = year_data.countries[old_name]
            # Merge old data into new normalized entry
            if normalized_country not in year_data.countries:
                # Create new entry with old data
                country_data = CountryRevenueData(
                    country=normalized_country,
                    membership_revenue=old_data.membership_revenue,
                    affiliate_revenue=old_data.affiliate_revenue
                )
                year_data.countries[normalized_country] = country_data
            else:
                # Merge: preserve old values if new ones aren't provided
                country_data = year_data.countries[normalized_country]
                if membership_revenue is None:
                    country_data.membership_revenue = old_data.membership_revenue
                if affiliate_revenue is None:
                    country_data.affiliate_revenue = old_data.affiliate_revenue
            
            # Delete old entry
            del year_data.countries[old_name]
            logger.info(f"Migrated '{old_name}' to '{normalized_country}' for year {year}")
        
        # Get or create country data
        if normalized_country in year_data.countries:
            country_data = year_data.countries[normalized_country]
            # Update only provided values, preserve others
            if membership_revenue is not None:
                country_data.membership_revenue = float(membership_revenue)
            if affiliate_revenue is not None:
                country_data.affiliate_revenue = float(affiliate_revenue)
        else:
            # Create new country data - use provided values or default to 0
            country_data = CountryRevenueData(
                country=normalized_country,
                membership_revenue=float(membership_revenue) if membership_revenue is not None else 0.0,
                affiliate_revenue=float(affiliate_revenue) if affiliate_revenue is not None else 0.0
            )
            year_data.countries[normalized_country] = country_data
        
        # Save to cache
        self._save_financial_data()
        
        return {
            "country": normalized_country,
            "membership_revenue": country_data.membership_revenue,
            "affiliate_revenue": country_data.affiliate_revenue,
            "total_revenue": country_data.total_revenue
        }
    
    def add_country(self, year: int, country: str, 
                   membership_revenue: float = 0.0,
                   affiliate_revenue: float = 0.0) -> Dict[str, Any]:
        """
        Add a new country with revenue data
        
        Args:
            year: Year to add country to
            country: Country name (will be normalized)
            membership_revenue: Membership revenue (default 0.0)
            affiliate_revenue: Affiliate revenue (default 0.0)
            
        Returns:
            New country data
        """
        return self.update_country_revenue(
            year=year,
            country=country,
            membership_revenue=membership_revenue,
            affiliate_revenue=affiliate_revenue
        )
    
    def delete_country(self, year: int, country: str) -> Dict[str, Any]:
        """
        Delete a country (set revenue to 0) or remove it entirely
        
        Args:
            year: Year to delete country from
            country: Country name (will be normalized)
            
        Returns:
            Result message
        """
        if self._cached_data is None:
            self._load_financial_data()
        
        # Normalize country name
        normalized_country = self.country_normalizer.normalize(country)
        
        year_data = self._cached_data.get_year(year)
        if not year_data:
            raise ValueError(f"No data found for year {year}")
        
        if normalized_country in year_data.countries:
            # Remove country entirely (or set to 0 - we'll remove it)
            del year_data.countries[normalized_country]
            
            # Save to cache
            self._save_financial_data()
            
            return {
                "status": "success",
                "message": f"Country '{normalized_country}' removed from year {year}"
            }
        else:
            raise ValueError(f"Country '{normalized_country}' not found for year {year}")
    
    def import_from_excel(self) -> Dict[str, Any]:
        """
        Import data from Excel file and update cache
        
        Returns:
            Result message with import statistics
        """
        try:
            # Parse Excel file
            new_data = self.parser.parse_excel()
            
            # Merge with existing data (preserve manual edits)
            if self._cached_data is None:
                self._cached_data = new_data
            else:
                # Merge years - Excel data takes precedence for years it contains
                existing_years = {y.year: y for y in self._cached_data.years}
                new_years = {y.year: y for y in new_data.years}
                
                # Update existing years or add new ones
                for year, year_data in new_years.items():
                    existing_years[year] = year_data
                
                # Rebuild years list
                self._cached_data.years = [existing_years[y] for y in sorted(existing_years.keys())]
                self._cached_data.years_available = sorted(existing_years.keys())
                self._cached_data.latest_year = max(self._cached_data.years_available) if self._cached_data.years_available else 2025
            
            # Save to cache
            self._save_financial_data()
            
            return {
                "status": "success",
                "message": f"Imported data from Excel file",
                "years": self._cached_data.years_available,
                "latest_year": self._cached_data.latest_year
            }
        except Exception as e:
            logger.error(f"Error importing from Excel: {e}")
            raise ValueError(f"Error importing from Excel: {str(e)}")
    
    def save_to_cache(self) -> Dict[str, Any]:
        """
        Explicitly save current data to cache file
        
        Returns:
            Result message
        """
        if self._cached_data is None:
            raise ValueError("No data to save")
        
        self._save_financial_data()
        
        return {
            "status": "success",
            "message": "Data saved to cache file",
            "cache_file": str(self.cache_file)
        }

