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

# Financial Data Models for 990 Forms
class FinancialYearData(BaseModel):
    year: int = Field(..., description="Tax year")
    total_revenue: float = Field(..., description="Total revenue for the year")
    total_expenses: float = Field(..., description="Total expenses for the year")
    net_income: float = Field(..., description="Net income (revenue - expenses)")
    
    # Revenue breakdown
    program_service_revenue: float = Field(..., description="Program service revenue")
    contributions_grants: float = Field(..., description="Contributions and grants")
    investment_income: float = Field(..., description="Investment income")
    other_revenue: float = Field(..., description="Other revenue")
    
    # Program service revenue breakdown
    membership_dues: Optional[float] = Field(None, description="Membership dues")
    meetings_conferences: Optional[float] = Field(None, description="Meetings and conferences")
    education_certification: Optional[float] = Field(None, description="Education and certification")
    project_management_fees: Optional[float] = Field(None, description="Project management fees")
    qualified_sponsorship_payments: Optional[float] = Field(None, description="Qualified sponsorship payments")
    other_program_services: Optional[float] = Field(None, description="Other program service revenue (special projects, grants, etc.)")
    
    # Expense breakdown
    salaries_compensation: float = Field(..., description="Salaries and compensation")
    other_expenses: float = Field(..., description="Other expenses")
    management_services: Optional[float] = Field(None, description="Management services (pre-2024)")
    
    # Detailed expense categories
    fees_for_services_legal: Optional[float] = Field(None, description="Fees for services - legal")
    fees_for_services_accounting: Optional[float] = Field(None, description="Fees for services - accounting")
    fees_for_services_investment: Optional[float] = Field(None, description="Fees for services - investment management")
    fees_for_services_other: Optional[float] = Field(None, description="Fees for services - other")
    
    # Major additional expense categories
    compensation_officers_directors: Optional[float] = Field(None, description="Compensation of officers and directors")
    land_building_equipment_cost: Optional[float] = Field(None, description="Land, building, and equipment costs")
    advertising: Optional[float] = Field(None, description="Advertising expenses")
    office_expenses: Optional[float] = Field(None, description="Office expenses")
    information_technology: Optional[float] = Field(None, description="Information technology expenses")
    royalties: Optional[float] = Field(None, description="Royalties")
    occupancy: Optional[float] = Field(None, description="Occupancy expenses")
    travel: Optional[float] = Field(None, description="Travel expenses")
    conferences_meetings: Optional[float] = Field(None, description="Conferences and meetings expenses")
    interest: Optional[float] = Field(None, description="Interest expenses")
    payments_to_affiliates: Optional[float] = Field(None, description="Payments to affiliates")
    depreciation: Optional[float] = Field(None, description="Depreciation and depletion")
    insurance: Optional[float] = Field(None, description="Insurance expenses")
    all_other_expenses: Optional[float] = Field(None, description="All other expenses")
    
    # Specific other expense categories (from OtherExpensesGrp)
    equipment_rental: Optional[float] = Field(None, description="Equipment rental")
    distance_elearning: Optional[float] = Field(None, description="Distance eLearning")
    credit_card_bank_fees: Optional[float] = Field(None, description="Credit card and bank fees")
    fees_licenses: Optional[float] = Field(None, description="Fees and licenses")
    exhibit_expense: Optional[float] = Field(None, description="Exhibit expenses")
    
    # Balance sheet data
    total_assets: float = Field(..., description="Total assets")
    total_liabilities: float = Field(..., description="Total liabilities")
    net_assets: float = Field(..., description="Net assets")
    
    # Employee data
    total_employees: int = Field(..., description="Total number of employees")
    total_volunteers: int = Field(..., description="Total number of volunteers")

class FinancialTrend(BaseModel):
    year: int = Field(..., description="Year")
    revenue: float = Field(..., description="Total revenue")
    expenses: float = Field(..., description="Total expenses")
    net_income: float = Field(..., description="Net income")
    revenue_growth: Optional[float] = Field(None, description="Revenue growth percentage")
    expense_growth: Optional[float] = Field(None, description="Expense growth percentage")

class RevenueComposition(BaseModel):
    year: int = Field(..., description="Year")
    program_services: float = Field(..., description="Program services revenue")
    contributions: float = Field(..., description="Contributions revenue")
    investment_income: float = Field(..., description="Investment income")
    other_revenue: float = Field(..., description="Other revenue")

class FinancialHealthMetrics(BaseModel):
    years: List[FinancialYearData] = Field(..., description="Financial data by year")
    revenue_trend: List[FinancialTrend] = Field(..., description="Revenue and expense trends")
    revenue_composition: List[RevenueComposition] = Field(..., description="Revenue composition by source")
    latest_year: int = Field(..., description="Latest year with data")
    years_available: List[int] = Field(..., description="Available years")

class FinancialChartData(BaseModel):
    labels: List[str] = Field(..., description="Chart labels (years)")
    datasets: List[Dict[str, Any]] = Field(..., description="Chart datasets")
    type: str = Field(..., description="Chart type")
    title: str = Field(..., description="Chart title") 