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

# Financial Data Models (used for compatibility with existing dashboard structure)
class FinancialYearData(BaseModel):
    year: int = Field(..., description="Tax year")
    total_revenue: float = Field(..., description="Total revenue for the year")
    total_expenses: float = Field(..., description="Total expenses for the year")
    net_income: float = Field(..., description="Net income (revenue - expenses)")
    
    # Revenue breakdown
    program_service_revenue: float = Field(..., description="Program service revenue")
    contributions_grants: float = Field(..., description="Federal grants and contracts")
    investment_income: float = Field(..., description="Investment income")
    other_revenue: float = Field(..., description="Other revenue")
    net_assets_released_from_restrictions: Optional[float] = Field(None, description="Net assets released from restrictions")
    
    # Program service revenue breakdown
    membership_dues: Optional[float] = Field(None, description="Membership dues (total)")
    membership_dues_organizational: Optional[float] = Field(None, description="Membership dues - Organizational")
    membership_dues_individuals: Optional[float] = Field(None, description="Membership dues - Individuals and affiliates")
    meetings_conferences: Optional[float] = Field(None, description="Meetings and conferences")
    education_certification: Optional[float] = Field(None, description="Education and certification")
    project_management_fees: Optional[float] = Field(None, description="Project management fees")
    other_program_services: Optional[float] = Field(None, description="Other program service revenue (special projects, grants, etc.)")
    
    # Expense breakdown (new structure matching audited financials)
    # Program Services Expenses
    membership_meetings_education_expenses: Optional[float] = Field(None, description="Membership, meetings and education expenses (Program Services)")
    standards_development_pmo_tooling_expenses: Optional[float] = Field(None, description="Standards development, PMO and tooling expenses (Program Services)")
    federal_grant_projects_expenses: Optional[float] = Field(None, description="Federal grant projects expenses (Program Services)")
    total_program_services_expenses: Optional[float] = Field(None, description="Total Program Services expenses (auto-calculated)")
    
    # Supporting Services Expenses
    management_general_expenses: Optional[float] = Field(None, description="Management and general expenses (Supporting Services)")
    membership_development_expenses: Optional[float] = Field(None, description="Membership development expenses (Supporting Services)")
    total_supporting_services_expenses: Optional[float] = Field(None, description="Total Supporting Services expenses (auto-calculated)")
    
    # Legacy expense fields (kept for backward compatibility)
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
    description: Optional[str] = Field(None, description="Chart description/note")

# Models for Audited Financial Statements
class FunctionalExpenseCategory(BaseModel):
    """Represents a single expense category with breakdown by function matching audited financials structure"""
    category_name: str = Field(..., description="Name of the expense category")
    # Program Services breakdown
    membership_meetings_education: float = Field(0.0, description="Membership, meetings and education (Program Services)")
    standards_development_pmo_tooling: float = Field(0.0, description="Standards development, PMO and tooling (Program Services)")
    federal_grant_projects: float = Field(0.0, description="Federal grant projects (Program Services)")
    program_services_total: Optional[float] = Field(None, description="Total Program Services (auto-calculated)")
    # Supporting Services breakdown
    management_general: float = Field(0.0, description="Management and general (Supporting Services)")
    membership_development: float = Field(0.0, description="Membership development (Supporting Services)")
    supporting_services_total: Optional[float] = Field(None, description="Total Supporting Services (auto-calculated)")
    # Total
    total: Optional[float] = Field(None, description="Total (auto-calculated)")
    
    # Legacy fields for backward compatibility
    program_services: Optional[float] = Field(None, description="Legacy: Amount allocated to Program Services")
    supporting_services: Optional[float] = Field(None, description="Legacy: Amount allocated to Supporting Services")

class FunctionalExpensesData(BaseModel):
    """Functional expenses breakdown for a single year"""
    year: int = Field(..., description="Year")
    categories: List[FunctionalExpenseCategory] = Field(..., description="Expense categories with functional breakdown")
    total_program_services: float = Field(..., description="Total Program Services expenses")
    total_supporting_services: float = Field(..., description="Total Supporting Services expenses")
    total_expenses: float = Field(..., description="Total expenses (should equal sum of all categories)")

class AuditedFinancialYearData(FinancialYearData):
    """Extended financial year data for audited financial statements"""
    functional_expenses: Optional[FunctionalExpensesData] = Field(None, description="Functional expenses breakdown")

class AuditedFinancialHealthMetrics(BaseModel):
    """Financial health metrics from audited financial statements"""
    years: List[AuditedFinancialYearData] = Field(..., description="Financial data by year")
    revenue_trend: List[FinancialTrend] = Field(..., description="Revenue and expense trends")
    revenue_composition: List[RevenueComposition] = Field(..., description="Revenue composition by source")
    latest_year: int = Field(..., description="Latest year with data")
    years_available: List[int] = Field(..., description="Available years")

# Consolidated Financial Data Models - Unified structure for Audited Financials and Budget data
class SourceValue(BaseModel):
    """Represents a value from a specific data source"""
    value: Optional[float] = Field(None, description="The value from this source")
    source: str = Field(..., description="Source identifier: 'audited', 'budget_draft', or 'budget_final'")
    last_updated: Optional[str] = Field(None, description="When this value was last updated")
    notes: Optional[str] = Field(None, description="Additional notes about this value")

class UnifiedFinancialValue(BaseModel):
    """A financial value that can come from multiple sources (audited, budget)"""
    field_name: str = Field(..., description="The field name (e.g., 'total_revenue', 'salaries_compensation')")
    values: List[SourceValue] = Field(default_factory=list, description="Values from different sources")
    
    def get_value(self, source: str) -> Optional[float]:
        """Get value from a specific source"""
        for v in self.values:
            if v.source == source:
                return v.value
        return None
    
    def get_audited_value(self) -> Optional[float]:
        """Get value from audited financial statements"""
        return self.get_value("audited")
    
    def get_budget_draft_value(self) -> Optional[float]:
        """Get draft budget value"""
        return self.get_value("budget_draft")
    
    def get_budget_final_value(self) -> Optional[float]:
        """Get final budget value"""
        return self.get_value("budget_final")
    
    def get_actual_value(self) -> Optional[float]:
        """Get actual value from audited data"""
        return self.get_audited_value()

class BudgetFunctionalExpenseCategory(BaseModel):
    """Budgeted functional expense category"""
    category_name: str = Field(..., description="Name of the expense category")
    program_services_draft: Optional[float] = Field(None, description="Draft budget - Program Services")
    supporting_services_draft: Optional[float] = Field(None, description="Draft budget - Supporting Services")
    total_draft: Optional[float] = Field(None, description="Draft budget - Total")
    program_services_final: Optional[float] = Field(None, description="Final budget - Program Services")
    supporting_services_final: Optional[float] = Field(None, description="Final budget - Supporting Services")
    total_final: Optional[float] = Field(None, description="Final budget - Total")

class BudgetData(BaseModel):
    """Budget data for a year (draft and final)"""
    year: int = Field(..., description="Budget year")
    version: str = Field(..., description="Budget version: 'draft' or 'final'")
    created_date: Optional[str] = Field(None, description="When this budget was created")
    approved_date: Optional[str] = Field(None, description="When this budget was approved")
    
    # Revenue
    total_revenue: Optional[float] = Field(None, description="Total budgeted revenue")
    program_service_revenue: Optional[float] = Field(None, description="Budgeted program service revenue")
    contributions_grants: Optional[float] = Field(None, description="Budgeted federal grants and contracts")
    investment_income: Optional[float] = Field(None, description="Budgeted investment income")
    other_revenue: Optional[float] = Field(None, description="Budgeted other revenue")
    
    # Program service revenue breakdown
    membership_dues: Optional[float] = Field(None, description="Budgeted membership dues (total)")
    membership_dues_organizational: Optional[float] = Field(None, description="Budgeted membership dues - Organizational")
    membership_dues_individuals: Optional[float] = Field(None, description="Budgeted membership dues - Individuals and international affiliates")
    meetings_conferences: Optional[float] = Field(None, description="Budgeted meetings and conferences")
    education_certification: Optional[float] = Field(None, description="Budgeted education and certification")
    project_management_fees: Optional[float] = Field(None, description="Budgeted project management fees")
    other_program_services: Optional[float] = Field(None, description="Budgeted other program services")
    
    # Expenses
    total_expenses: Optional[float] = Field(None, description="Total budgeted expenses")
    salaries_compensation: Optional[float] = Field(None, description="Budgeted salaries and compensation")
    other_expenses: Optional[float] = Field(None, description="Budgeted other expenses")
    
    # Functional expenses (if available)
    functional_expenses: Optional[List[BudgetFunctionalExpenseCategory]] = Field(None, description="Budgeted functional expenses breakdown")
    total_program_services: Optional[float] = Field(None, description="Total budgeted Program Services expenses")
    total_supporting_services: Optional[float] = Field(None, description="Total budgeted Supporting Services expenses")
    
    # Balance sheet projections
    total_assets: Optional[float] = Field(None, description="Projected total assets")
    total_liabilities: Optional[float] = Field(None, description="Projected total liabilities")
    net_assets: Optional[float] = Field(None, description="Projected net assets")
    
    # Notes
    notes: Optional[str] = Field(None, description="Additional notes about this budget")

class ConsolidatedFinancialYearData(BaseModel):
    """Consolidated financial data for a single year from audited financial statements and budgets"""
    year: int = Field(..., description="Fiscal year")
    
    # Data from each source
    audited: Optional[AuditedFinancialYearData] = Field(None, description="Data from audited financial statements")
    budget_draft: Optional[BudgetData] = Field(None, description="Draft budget data")
    budget_final: Optional[BudgetData] = Field(None, description="Final approved budget data")
    
    # Computed comparison metrics
    revenue_variance_draft: Optional[float] = Field(None, description="Revenue variance vs draft budget (actual - draft)")
    revenue_variance_final: Optional[float] = Field(None, description="Revenue variance vs final budget (actual - final)")
    expense_variance_draft: Optional[float] = Field(None, description="Expense variance vs draft budget (actual - draft)")
    expense_variance_final: Optional[float] = Field(None, description="Expense variance vs final budget (actual - final)")
    
    # Helper methods to get values from audited data
    def get_total_revenue(self) -> Optional[float]:
        """Get total revenue from audited data"""
        if self.audited:
            return self.audited.total_revenue
        return None
    
    def get_total_expenses(self) -> Optional[float]:
        """Get total expenses from audited data"""
        if self.audited:
            return self.audited.total_expenses
        return None
    
    def get_net_income(self) -> Optional[float]:
        """Get net income from audited data"""
        if self.audited:
            return self.audited.net_income
        return None

class ConsolidatedFinancialData(BaseModel):
    """Consolidated financial data across all years and all sources"""
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about the consolidated data")
    years: List[ConsolidatedFinancialYearData] = Field(..., description="Financial data by year")
    years_available: List[int] = Field(..., description="Available years")
    latest_year: int = Field(..., description="Latest year with data")
    
    def get_year(self, year: int) -> Optional[ConsolidatedFinancialYearData]:
        """Get data for a specific year"""
        for y in self.years:
            if y.year == year:
                return y
        return None
    
    def get_years_with_budget(self) -> List[int]:
        """Get years that have budget data (draft or final)"""
        return [y.year for y in self.years if y.budget_draft or y.budget_final]
    
    def get_years_with_audited(self) -> List[int]:
        """Get years that have audited financial data"""
        return [y.year for y in self.years if y.audited]

# Geographic Financial Data Models
class CountryRevenueData(BaseModel):
    """Revenue data for a specific country"""
    country: str = Field(..., description="Country name")
    membership_revenue: float = Field(0.0, description="Membership revenue from this country")
    affiliate_revenue: float = Field(0.0, description="Affiliate revenue from this country")
    
    @property
    def total_revenue(self) -> float:
        """Total revenue (membership + affiliate)"""
        return self.membership_revenue + self.affiliate_revenue

class GeographicYearData(BaseModel):
    """Geographic financial data for a specific year"""
    year: int = Field(..., description="Year")
    countries: Dict[str, CountryRevenueData] = Field(default_factory=dict, description="Revenue data by country")
    
    @property
    def total_membership_revenue(self) -> float:
        """Total membership revenue across all countries"""
        return sum(c.membership_revenue for c in self.countries.values())
    
    @property
    def total_affiliate_revenue(self) -> float:
        """Total affiliate revenue across all countries"""
        return sum(c.affiliate_revenue for c in self.countries.values())
    
    @property
    def total_revenue(self) -> float:
        """Total revenue (membership + affiliate) across all countries"""
        return self.total_membership_revenue + self.total_affiliate_revenue
    
    @property
    def non_us_membership_revenue(self) -> float:
        """Total membership revenue excluding United States"""
        return sum(c.membership_revenue for country, c in self.countries.items() 
                   if country.lower() not in ['united states', 'usa', 'us'])
    
    @property
    def non_us_affiliate_revenue(self) -> float:
        """Total affiliate revenue excluding United States (includes Other category)"""
        return sum(c.affiliate_revenue for country, c in self.countries.items() 
                   if country.lower() not in ['united states', 'usa', 'us'])

class GeographicFinancialMetrics(BaseModel):
    """Geographic financial metrics and summary"""
    years: List[GeographicYearData] = Field(..., description="Geographic data by year")
    years_available: List[int] = Field(..., description="Available years")
    latest_year: int = Field(..., description="Latest year with data")
    
    def get_year(self, year: int) -> Optional[GeographicYearData]:
        """Get data for a specific year"""
        for y in self.years:
            if y.year == year:
                return y
        return None
    
    def get_latest_data(self) -> Optional[GeographicYearData]:
        """Get data for the latest year"""
        return self.get_year(self.latest_year) 