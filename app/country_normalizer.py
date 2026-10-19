"""
Country name normalization service using World Bank API (wbgapi)
Converts country names to World Bank standard names
"""
import wbgapi as wb
import logging
from typing import Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class CountryNormalizer:
    """
    Normalize country names to World Bank standard names.
    
    Important: Territories and dependencies are kept separate from their parent countries.
    For example, if "French Guiana" appears in the data, it will remain as "French Guiana"
    and NOT be normalized to "France", even though French Guiana is a French territory.
    This ensures that if the World Bank or the data source distinguishes them, they remain separate.
    """
    
    def __init__(self):
        self._country_cache: Dict[str, str] = {}
        self._load_world_bank_countries()
    
    def _load_world_bank_countries(self):
        """Load World Bank country names and create lookup maps"""
        try:
            # Get all countries from World Bank API
            countries = wb.economy.list()
            
            # Create mappings from various name formats to WB standard name
            for country in countries:
                wb_name = country.get('value', '') or country.get('name', '')  # WB API uses 'value' field
                wb_id = country.get('id', '')
                
                if not wb_name:
                    continue
                
                # Store by WB name (standard) - preserve exact case as returned by WB
                self._country_cache[wb_name.lower()] = wb_name
                
                # Store by WB ID (ISO 3-letter code)
                if wb_id:
                    self._country_cache[wb_id.lower()] = wb_name
                    self._country_cache[wb_id.upper()] = wb_name
                
            # Load common variations
            self._load_common_variations()
            
            logger.info(f"Loaded {len(self._country_cache)} country name mappings from World Bank")
        except Exception as e:
            logger.warning(f"Error loading World Bank countries: {e}. Using fallback mappings.")
            self._load_fallback_mappings()
    
    def _store_variations(self, original: str, wb_name: str):
        """Store common variations of country names"""
        # This method is called for each WB country, but we'll store variations globally
        pass
    
    def _load_common_variations(self):
        """Load common country name variations to World Bank standard names
        
        Note: We do NOT map territories/dependencies to their parent countries.
        For example, French Guiana stays as "French Guiana", not "France".
        This ensures that if data distinguishes them, they remain separate.
        """
        variations = {
            'uk': 'United Kingdom',
            'united kingdom': 'United Kingdom',
            'usa': 'United States',
            'us': 'United States',
            'u.s.': 'United States',
            'u.s.a.': 'United States',
            'united states': 'United States',
            'united states of america': 'United States',
            'korea': 'Korea, Rep.',
            'south korea': 'Korea, Rep.',
            'north korea': 'Korea, Dem. People\'s Rep.',
            'russia': 'Russian Federation',
            'russian federation': 'Russian Federation',
            'uae': 'United Arab Emirates',
            'united arab emirates': 'United Arab Emirates',
            'czech republic': 'Czechia',
            'czechia': 'Czechia',
            'slovak republic': 'Slovak Republic',
            'slovakia': 'Slovak Republic',
            'vietnam': 'Vietnam',
            'iran': 'Iran, Islamic Rep.',
            'syria': 'Syrian Arab Republic',
            'venezuela': 'Venezuela, RB',
            'yemen': 'Yemen, Rep.',
            'egypt': 'Egypt, Arab Rep.',
            'laos': 'Lao PDR',
            'myanmar': 'Myanmar',
            'burma': 'Myanmar',
            'macedonia': 'North Macedonia',
            'congo': 'Congo, Rep.',
            'democratic republic of congo': 'Congo, Dem. Rep.',
            'drc': 'Congo, Dem. Rep.',
            'ivory coast': 'Cote d\'Ivoire',
            'cote d\'ivoire': 'Cote d\'Ivoire',
            'east timor': 'Timor-Leste',
            'saint kitts': 'St. Kitts and Nevis',
            'saint lucia': 'St. Lucia',
            'saint vincent': 'St. Vincent and the Grenadines',
            'sao tome': 'Sao Tome and Principe',
            'bosnia': 'Bosnia and Herzegovina',
            'trinidad': 'Trinidad and Tobago',
            'antigua': 'Antigua and Barbuda',
            # Taiwan mapping
            'taiwan': 'Taiwan, China',
            # Also add Taiwan, China as a valid normalized name (so it doesn't get re-normalized)
            'taiwan, china': 'Taiwan, China',
            # Central America special case
            'central america': 'Central America and Dominican Republic',
            'central america and dominican republic': 'Central America and Dominican Republic',
            # Other/International Affiliates special case (for non-mappable affiliate revenue)
            'other': 'Other (International Affiliates)',
            'international affiliates': 'Other (International Affiliates)',
            'international affiliate': 'Other (International Affiliates)',
            'other (international affiliates)': 'Other (International Affiliates)',
            # Note: We explicitly do NOT map French Guiana to France
            # If French Guiana appears in data, it should remain separate
            'french guiana': 'French Guiana',  # Keep separate if it exists
        }
        
        for key, value in variations.items():
            self._country_cache[key.lower()] = value
    
    def _load_fallback_mappings(self):
        """Load fallback mappings if World Bank API fails"""
        fallback_mappings = {
            'united states': 'United States',
            'usa': 'United States',
            'us': 'United States',
            'uk': 'United Kingdom',
            'united kingdom': 'United Kingdom',
            'korea': 'Korea, Rep.',
            'south korea': 'Korea, Rep.',
            'russia': 'Russian Federation',
            'uae': 'United Arab Emirates',
            'czech republic': 'Czechia',
            'czechia': 'Czechia',
            'slovak republic': 'Slovak Republic',
            'slovakia': 'Slovak Republic',
        }
        
        for key, value in fallback_mappings.items():
            self._country_cache[key.lower()] = value
    
    @lru_cache(maxsize=1000)
    def normalize(self, country_name: str) -> str:
        """
        Normalize a country name to World Bank standard name
        
        Args:
            country_name: The country name to normalize
            
        Returns:
            World Bank standard country name, or original name if not found
        """
        if not country_name:
            return country_name
        
        country_name = country_name.strip()
        
        # Try exact match first
        normalized = self._country_cache.get(country_name.lower())
        if normalized:
            return normalized
        
        # Try title case
        normalized = self._country_cache.get(country_name.title().lower())
        if normalized:
            return normalized
        
        # Try to find by partial match
        country_lower = country_name.lower()
        for key, value in self._country_cache.items():
            if country_lower in key or key in country_lower:
                # Prefer exact matches
                if country_lower == key:
                    return value
                # Use partial match as fallback
                if len(key) > 3:  # Avoid very short partial matches
                    return value
        
        # If not found, try to match with World Bank countries directly
        try:
            # Search World Bank countries
            countries = list(wb.economy.list(q=country_name))
            if countries:
                # Return the first match - use 'value' field which contains the country name
                wb_match = countries[0].get('value') or countries[0].get('name', '')
                if wb_match:
                    return wb_match
        except Exception as e:
            logger.debug(f"Error searching World Bank for '{country_name}': {e}")
        
        # Return original name if no match found
        # This preserves territories/dependencies that may not be in World Bank but should be kept separate
        logger.debug(f"Could not normalize country name: '{country_name}', returning as-is")
        return country_name
    
    def get_wb_country_code(self, country_name: str) -> Optional[str]:
        """
        Get World Bank country code (ISO 3-letter) for a country name
        
        Args:
            country_name: The country name
            
        Returns:
            World Bank country code (ISO 3-letter) or None if not found
        """
        normalized = self.normalize(country_name)
        
        try:
            countries = wb.economy.list(q=normalized)
            if countries:
                return countries[0].get('id')
        except Exception as e:
            logger.debug(f"Error getting WB code for '{country_name}': {e}")
        
        return None

# Global instance
_country_normalizer = None

def get_country_normalizer() -> CountryNormalizer:
    """Get the global country normalizer instance"""
    global _country_normalizer
    if _country_normalizer is None:
        _country_normalizer = CountryNormalizer()
    return _country_normalizer

