import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.models import (
    KPIData, KPIIndicator, KPIMeasurement, KPICard, KPITrend, 
    KPISummary, KPIMetadata, KPIFilter, ChartData, DashboardMetrics
)

class DataService:
    def __init__(self, json_path: str = "data/processed/kpi_data.json"):
        self.json_path = Path(json_path)
        self._data = None
        self._load_data()
    
    def _load_data(self):
        """Load and validate JSON data"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")
        
        try:
            with open(self.json_path, 'r') as f:
                data_dict = json.load(f)
            
            self._data = KPIData(**data_dict)
        except Exception as e:
            raise ValueError(f"Error loading JSON data: {e}")
    
    def reload_data(self):
        """Reload data from the JSON file"""
        self._load_data()
    
    def get_kpi_data(self) -> Optional[KPIData]:
        """Get the complete KPI data"""
        return self._data
    
    def get_indicators_by_steward(self, steward: str) -> List[KPIIndicator]:
        """Get all indicators for a specific steward"""
        if not self._data:
            return []
        
        return [
            indicator for indicator in self._data.indicators.values()
            if steward in indicator.stewards
        ]
    
    def get_indicators_by_domain(self, domain: str) -> List[KPIIndicator]:
        """Get all indicators for a specific domain"""
        if not self._data:
            return []
        
        return [
            indicator for indicator in self._data.indicators.values()
            if indicator.domain == domain
        ]
    
    def get_indicator_by_id(self, indicator_id: str) -> Optional[KPIIndicator]:
        """Get a specific indicator by ID"""
        if not self._data:
            return None
        
        return self._data.indicators.get(indicator_id)
    
    def calculate_trend(self, indicator: KPIIndicator) -> Optional[KPITrend]:
        """Calculate trend between the two most recent time periods"""
        if not self._data or len(self._data.metadata.time_periods) < 2:
            return None
        
        # Get the two most recent time periods
        if not self._data:
            return None
        time_periods = sorted(self._data.metadata.time_periods)
        current_period = time_periods[-1]
        previous_period = time_periods[-2]
        
        # Get measurements for both periods
        current_measurement = indicator.measurements.get(current_period)
        previous_measurement = indicator.measurements.get(previous_period)
        
        if not current_measurement or not previous_measurement:
            return None
        
        if current_measurement.value is None or previous_measurement.value is None:
            return None
        
        current_value = current_measurement.value
        previous_value = previous_measurement.value
        
        # Calculate percentage change
        if previous_value == 0:
            change_pct = 100.0 if current_value > 0 else 0.0
        else:
            # Handle the case where we transition from negative to positive or vice versa
            # Use absolute value of previous value to avoid sign flipping issues
            if (previous_value < 0 and current_value > 0) or (previous_value > 0 and current_value < 0):
                # When crossing zero, use absolute value of previous value as denominator
                change_pct = ((current_value - previous_value) / abs(previous_value)) * 100
            else:
                # Standard percentage change calculation for same-sign values
                change_pct = ((current_value - previous_value) / previous_value) * 100
        
        # Determine trend direction
        if change_pct > 0:
            trend = "up"
        elif change_pct < 0:
            trend = "down"
        else:
            trend = "stable"
        
        return KPITrend(
            current=current_value,
            previous=previous_value,
            change_pct=change_pct,
            trend=trend
        )
    
    def calculate_progress_to_target(self, indicator: KPIIndicator) -> tuple[Optional[float], Optional[str], Optional[float]]:
        """Calculate progress percentage towards target and return (progress, target_type, target_value)"""
        if not self._data:
            return None, None, None
        time_periods = sorted(self._data.metadata.time_periods)
        current_period = time_periods[-1]
        current_year = current_period.split("-")[0] if "-" in current_period else None
        current_measurement = indicator.measurements.get(current_period)
        
        if not current_measurement or current_measurement.value is None:
            return None, None, None
        
        current_value = current_measurement.value
        
        # 1. Check for period-specific target
        if current_measurement.target is not None:
            target = current_measurement.target
            target_type = "period"
        # 2. Check for annual target
        elif indicator.targets and current_year in indicator.targets:
            target = indicator.targets[current_year]
            target_type = "annual"
            # Calculate year value based on target operation
            year_values = []
            for period, measurement in indicator.measurements.items():
                if period.startswith(current_year) and measurement.value is not None:
                    year_values.append(measurement.value)
            
            if year_values:
                if indicator.target_operation == 'average':
                    current_value = sum(year_values) / len(year_values)
                else:  # Default to sum
                    current_value = sum(year_values)
            else:
                current_value = 0.0
        # 3. Fallback to legacy indicator.target
        elif indicator.target is not None:
            target = indicator.target
            target_type = "legacy"
        else:
            return None, "none", None
        
        if target == 0:
            return (100.0 if current_value == 0 else 0.0), target_type, target
        
        progress = (current_value / target) * 100
        return progress, target_type, target  # Allow progress to exceed 100% for exceeded targets
    
    def create_kpi_card(self, indicator: KPIIndicator) -> KPICard:
        """Create a KPI card with current data, trend, and target progress"""
        # Get current and previous values
        if not self._data:
            return KPICard(
                indicator=indicator,
                current_value=None,
                previous_value=None,
                trend=None,
                progress_to_target=None,
                target_type=None,
                target_value=None
            )
        time_periods = sorted(self._data.metadata.time_periods)
        current_period = time_periods[-1]
        previous_period = time_periods[-2] if len(time_periods) > 1 else None
        
        current_measurement = indicator.measurements.get(current_period)
        previous_measurement = indicator.measurements.get(previous_period) if previous_period else None
        
        current_value = current_measurement.value if current_measurement else None
        previous_value = previous_measurement.value if previous_measurement else None
        
        # Calculate trend
        trend = self.calculate_trend(indicator)
        
        # Calculate progress to target
        progress_to_target, target_type, target_value = self.calculate_progress_to_target(indicator)
        
        return KPICard(
            indicator=indicator,
            current_value=current_value,
            previous_value=previous_value,
            trend=trend,
            progress_to_target=progress_to_target,
            target_type=target_type,
            target_value=target_value
        )
    
    def get_kpi_cards(self, steward: Optional[str] = None, domain: Optional[str] = None, kpi_only: bool = False, tag_filter: Optional[str] = None) -> List[KPICard]:
        """Get KPI cards with optional filtering"""
        if not self._data:
            return []
        
        indicators = []
        
        # Start with all indicators
        indicators = list(self._data.indicators.values())
        
        # Apply steward filter if provided
        if steward:
            indicators = [ind for ind in indicators if steward in ind.stewards]
        
        # Apply domain filter if provided
        if domain:
            indicators = [ind for ind in indicators if ind.domain == domain]
        
        # Apply KPI filter if requested
        if kpi_only:
            indicators = [ind for ind in indicators if "KPI" in ind.tags]
        
        # Apply tag filter if provided
        if tag_filter:
            indicators = [ind for ind in indicators if tag_filter in ind.tags]
        
        # Sort indicators by domain first, then by name
        indicators.sort(key=lambda x: (x.domain, x.name))
        
        return [self.create_kpi_card(indicator) for indicator in indicators]
    
    def get_kpi_summary(self, steward: Optional[str] = None, domain: Optional[str] = None, tag_filter: Optional[str] = None) -> KPISummary:
        """Generate summary statistics with optional filtering"""
        if not self._data:
            return KPISummary(
                total_indicators=0,
                indicators_by_domain={},
                indicators_by_steward={},
                time_periods=[],
                latest_period=""
            )
        
        indicators = list(self._data.indicators.values())
        
        # Apply steward filter if provided
        if steward:
            indicators = [ind for ind in indicators if steward in ind.stewards]
        
        # Apply domain filter if provided
        if domain:
            indicators = [ind for ind in indicators if ind.domain == domain]
        
        # Apply tag filter if provided
        if tag_filter:
            indicators = [ind for ind in indicators if tag_filter in ind.tags]
        
        # Count by domain
        domain_counts = {}
        for indicator in indicators:
            domain = indicator.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Count by steward
        steward_counts = {}
        for indicator in indicators:
            # Count each steward for this indicator
            for steward_name in indicator.stewards:
                steward_counts[steward_name] = steward_counts.get(steward_name, 0) + 1
        
        time_periods = self._data.metadata.time_periods
        latest_period = sorted(time_periods)[-1] if time_periods else ""
        
        return KPISummary(
            total_indicators=len(indicators),
            indicators_by_domain=domain_counts,
            indicators_by_steward=steward_counts,
            time_periods=time_periods,
            latest_period=latest_period
        )
    
    def get_dashboard_metrics(self, steward: Optional[str] = None) -> DashboardMetrics:
        """Get complete dashboard metrics for a steward"""
        if not self._data:
            return DashboardMetrics(
                kpi_cards=[],
                summary=KPISummary(
                    total_indicators=0,
                    indicators_by_domain={},
                    indicators_by_steward={},
                    time_periods=[],
                    latest_period=""
                ),
                metadata=KPIMetadata(
                    version="",
                    last_updated="",
                    data_source="",
                    time_periods=[],
                    domains=[],
                    stewards=[]
                )
            )
        
        kpi_cards = self.get_kpi_cards(steward=steward)
        summary = self.get_kpi_summary(steward=steward)
        
        return DashboardMetrics(
            kpi_cards=kpi_cards,
            summary=summary,
            metadata=self._data.metadata
        )
    
    def get_chart_data(self, chart_type: str = "domain_distribution", steward: Optional[str] = None) -> ChartData:
        """Generate chart data for different visualizations"""
        if not self._data:
            return ChartData(labels=[], values=[], colors=None, type="bar")
        
        indicators = list(self._data.indicators.values())
        if steward:
            indicators = [ind for ind in indicators if steward in ind.stewards]
        
        if chart_type == "domain_distribution":
            domain_counts = {}
            for indicator in indicators:
                domain = indicator.domain
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            return ChartData(
                labels=list(domain_counts.keys()),
                values=list(domain_counts.values()),
                colors=None,
                type="pie"
            )
        
        elif chart_type == "trend_comparison":
            # Compare current vs previous values for key indicators
            if not self._data:
                return ChartData(labels=[], values=[], colors=None, type="bar")
            time_periods = sorted(self._data.metadata.time_periods)
            if len(time_periods) < 2:
                return ChartData(labels=[], values=[], colors=None, type="bar")
            
            current_period = time_periods[-1]
            previous_period = time_periods[-2]
            
            labels = []
            current_values = []
            previous_values = []
            
            for indicator in indicators[:10]:  # Limit to first 10 for readability
                current_measurement = indicator.measurements.get(current_period)
                previous_measurement = indicator.measurements.get(previous_period)
                
                if current_measurement and previous_measurement:
                    if current_measurement.value is not None and previous_measurement.value is not None:
                        labels.append(indicator.name[:20] + "..." if len(indicator.name) > 20 else indicator.name)
                        current_values.append(current_measurement.value)
                        previous_values.append(previous_measurement.value)
            
            return ChartData(
                labels=labels,
                values=current_values + previous_values,
                colors=None,
                type="grouped_bar"
            )
        
        return ChartData(labels=[], values=[], colors=None, type="bar")
    
    def get_metadata(self) -> Optional[KPIMetadata]:
        """Get data metadata"""
        return self._data.metadata if self._data else None 