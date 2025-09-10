from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class KPIMeasurement(BaseModel):
    value: Optional[float] = Field(None, description="KPI measurement value")
    target: Optional[float] = Field(None, description="Period-specific target value")
    notes: Optional[str] = Field(None, description="Additional notes for this measurement")

class KPIIndicator(BaseModel):
    id: str = Field(..., description="Unique identifier for the KPI")
    name: str = Field(..., description="KPI indicator name")
    description: str = Field(..., description="Detailed description of the KPI")
    domain: str = Field(..., description="KPI domain/category")
    stewards: List[str] = Field(..., description="Organizations responsible for the KPI (primary steward first)")
    primary_steward: str = Field(..., description="Primary organization responsible for the KPI")
    type: str = Field(..., description="Measurement type (N, %, etc.)")
    unit: str = Field(..., description="Unit of measurement")
    target: Optional[float] = Field(None, description="Legacy target value for the KPI")
    targets: Optional[Dict[str, float]] = Field(None, description="Annual targets by year")
    target_operation: Optional[str] = Field(None, description="Operation for annual targets: 'sum' or 'average'")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing indicators (KPI, ACCELERATOR, etc.)")
    image: Optional[str] = Field(None, description="Optional image filename for the indicator card")
    trend_direction: str = Field("higher", description="Whether higher or lower values are better: 'higher' or 'lower'")
    measurements: Dict[str, KPIMeasurement] = Field(..., description="Measurements by time period")

class KPIMetadata(BaseModel):
    version: str = Field(..., description="Data version")
    last_updated: str = Field(..., description="Last update timestamp")
    data_source: str = Field(..., description="Data source identifier")
    time_periods: List[str] = Field(..., description="Available time periods")
    domains: List[str] = Field(..., description="Available domains")
    stewards: List[str] = Field(..., description="Available stewards")
    refresh_timestamp: Optional[int] = Field(None, description="Unix timestamp for cache busting")

class KPIData(BaseModel):
    metadata: KPIMetadata = Field(..., description="Data metadata")
    indicators: Dict[str, KPIIndicator] = Field(..., description="KPI indicators")

class KPITrend(BaseModel):
    current: float = Field(..., description="Current period value")
    previous: float = Field(..., description="Previous period value")
    change_pct: float = Field(..., description="Percentage change")
    trend: str = Field(..., description="Trend direction (up/down/stable)")

class KPICard(BaseModel):
    indicator: KPIIndicator = Field(..., description="KPI indicator data")
    current_value: Optional[float] = Field(None, description="Current period value")
    previous_value: Optional[float] = Field(None, description="Previous period value")
    trend: Optional[KPITrend] = Field(None, description="Trend information")
    progress_to_target: Optional[float] = Field(None, description="Progress percentage towards target")
    target_type: Optional[str] = Field(None, description="Type of target: 'period', 'annual', 'legacy', or 'none'")
    target_value: Optional[float] = Field(None, description="The target value being used for progress calculation")

class KPISummary(BaseModel):
    total_indicators: int = Field(..., description="Total number of indicators")
    indicators_by_domain: Dict[str, int] = Field(..., description="Indicator count by domain")
    indicators_by_steward: Dict[str, int] = Field(..., description="Indicator count by steward")
    time_periods: List[str] = Field(..., description="Available time periods")
    latest_period: str = Field(..., description="Latest time period")

class DashboardMetrics(BaseModel):
    kpi_cards: List[KPICard] = Field(..., description="KPI cards for display")
    summary: KPISummary = Field(..., description="Summary statistics")
    metadata: KPIMetadata = Field(..., description="Data metadata")

class KPIFilter(BaseModel):
    time_period: Optional[str] = None
    domain: Optional[str] = None
    steward: Optional[str] = None
    indicator: Optional[str] = None

class ChartData(BaseModel):
    labels: List[str] = Field(..., description="Chart labels")
    values: List[float] = Field(..., description="Chart values")
    colors: Optional[List[str]] = Field(None, description="Chart colors")
    type: str = Field("bar", description="Chart type") 