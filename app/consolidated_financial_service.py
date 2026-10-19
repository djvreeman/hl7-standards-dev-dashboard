"""
Service for managing consolidated financial data from multiple sources:
- Audited financial statements (primary source)
- Budget data (draft and final)
"""
import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

# HL7 Brand Color Palette
HL7_COLORS = {
    "brand_red": "#dc2626",        # Primary brand color
    "brand_red_alt": "#ec2227",    # Alternative red
    "success_green": "#16a34a",    # Success/positive
    "success_green_alt": "#0f8e48", # Alternative green
    "warning_yellow": "#ca8a04",   # Warning
    "danger_orange": "#ea580c",    # Danger/negative
    "neutral_gray": "#6b7280",     # Neutral/secondary
    # Variations for charts (lighter/darker shades)
    "brand_red_light": "rgba(220, 38, 38, 0.1)",
    "success_green_light": "rgba(22, 163, 74, 0.1)",
    "warning_yellow_light": "rgba(202, 138, 4, 0.1)",
    "danger_orange_light": "rgba(234, 88, 12, 0.1)",
    "neutral_gray_light": "rgba(107, 114, 128, 0.1)",
}
from app.models import (
    ConsolidatedFinancialData, ConsolidatedFinancialYearData,
    FinancialYearData, AuditedFinancialYearData, BudgetData,
    FinancialHealthMetrics, AuditedFinancialHealthMetrics,
    FinancialTrend, RevenueComposition, FinancialChartData
)

def _convert_audited_to_financial_year_data(audited_data: AuditedFinancialYearData) -> FinancialYearData:
    """Convert AuditedFinancialYearData to FinancialYearData format"""
    return FinancialYearData(
        year=audited_data.year,
        total_revenue=audited_data.total_revenue,
        total_expenses=audited_data.total_expenses,
        net_income=audited_data.net_income,
        program_service_revenue=audited_data.program_service_revenue,
        contributions_grants=audited_data.contributions_grants,
        investment_income=audited_data.investment_income,
        other_revenue=audited_data.other_revenue,
        membership_dues=audited_data.membership_dues,
        meetings_conferences=audited_data.meetings_conferences,
        education_certification=audited_data.education_certification,
        project_management_fees=audited_data.project_management_fees,
        other_program_services=audited_data.other_program_services,
        salaries_compensation=audited_data.salaries_compensation,
        other_expenses=audited_data.other_expenses,
        management_services=audited_data.management_services,
        fees_for_services_legal=audited_data.fees_for_services_legal,
        fees_for_services_accounting=audited_data.fees_for_services_accounting,
        fees_for_services_investment=audited_data.fees_for_services_investment,
        fees_for_services_other=audited_data.fees_for_services_other,
        compensation_officers_directors=audited_data.compensation_officers_directors,
        land_building_equipment_cost=audited_data.land_building_equipment_cost,
        advertising=audited_data.advertising,
        office_expenses=audited_data.office_expenses,
        information_technology=audited_data.information_technology,
        royalties=audited_data.royalties,
        occupancy=audited_data.occupancy,
        travel=audited_data.travel,
        conferences_meetings=audited_data.conferences_meetings,
        interest=audited_data.interest,
        payments_to_affiliates=audited_data.payments_to_affiliates,
        depreciation=audited_data.depreciation,
        insurance=audited_data.insurance,
        all_other_expenses=audited_data.all_other_expenses,
        equipment_rental=audited_data.equipment_rental,
        distance_elearning=audited_data.distance_elearning,
        credit_card_bank_fees=audited_data.credit_card_bank_fees,
        fees_licenses=audited_data.fees_licenses,
        exhibit_expense=audited_data.exhibit_expense,
        total_assets=audited_data.total_assets,
        total_liabilities=audited_data.total_liabilities,
        net_assets=audited_data.net_assets,
        total_employees=audited_data.total_employees,
        total_volunteers=audited_data.total_volunteers
    )
from app.audited_financials_service import AuditedFinancialsService

class ConsolidatedFinancialService:
    """Service for managing consolidated financial data from audited financial statements and budgets"""
    
    def __init__(
        self,
        cache_file: str = "data/processed/financial_data_consolidated.json",
        audited_service: Optional[AuditedFinancialsService] = None
    ):
        self.cache_file = Path(cache_file)
        self.audited_service = audited_service or AuditedFinancialsService()
        self._cached_data: Optional[ConsolidatedFinancialData] = None
        
        # Try to use the editor service's file first (single source of truth)
        from app.financial_data_editor_service import FinancialDataEditorService
        self.editor_service = FinancialDataEditorService()
    
    def get_consolidated_data(self) -> ConsolidatedFinancialData:
        """Get consolidated financial data, using cache if available"""
        if self._cached_data is None:
            self._load_consolidated_data()
        return self._cached_data
    
    def _load_consolidated_data(self):
        """Load consolidated data from the single consolidated file (via editor service)"""
        try:
            # Try to load from editor service (single source of truth)
            if self.editor_service.data_file.exists():
                self._cached_data = self.editor_service.load_data()
                return
        except Exception as e:
            print(f"Error loading from editor service: {e}")
        
        # Fallback to old cache file if editor service file doesn't exist
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data_dict = json.load(f)
                self._cached_data = ConsolidatedFinancialData(**data_dict)
                # Migrate to new file
                self.editor_service._cached_data = self._cached_data
                self.editor_service.save_data()
                return
            except Exception as e:
                print(f"Error loading cached consolidated data: {e}")
        
        # Build consolidated data from sources
        self._cached_data = self._build_consolidated_data()
        # Save to editor service file
        self.editor_service._cached_data = self._cached_data
        self.editor_service.save_data()
    
    def _build_consolidated_data(self) -> ConsolidatedFinancialData:
        """Build consolidated data from audited financial statements and budget sources"""
        # Get data from audited source
        audited_metrics = self.audited_service.get_financial_health_metrics()
        
        # Collect all unique years from audited data
        all_years = set()
        all_years.update([y.year for y in audited_metrics.years])
        # TODO: Add years from budget data when available
        
        all_years = sorted(list(all_years))
        
        # Build consolidated year data
        consolidated_years = []
        for year in all_years:
            # Get audited data for this year
            audited_data = next((y for y in audited_metrics.years if y.year == year), None)
            
            # TODO: Load budget data for this year
            budget_draft = None
            budget_final = None
            
            # Calculate variances if we have both actual and budget data
            revenue_variance_draft = None
            revenue_variance_final = None
            expense_variance_draft = None
            expense_variance_final = None
            
            if budget_draft and audited_data:
                if audited_data.total_revenue and budget_draft.total_revenue:
                    revenue_variance_draft = audited_data.total_revenue - budget_draft.total_revenue
                if audited_data.total_expenses and budget_draft.total_expenses:
                    expense_variance_draft = audited_data.total_expenses - budget_draft.total_expenses
            
            if budget_final and audited_data:
                if audited_data.total_revenue and budget_final.total_revenue:
                    revenue_variance_final = audited_data.total_revenue - budget_final.total_revenue
                if audited_data.total_expenses and budget_final.total_expenses:
                    expense_variance_final = audited_data.total_expenses - budget_final.total_expenses
            
            consolidated_year = ConsolidatedFinancialYearData(
                year=year,
                audited=audited_data,
                budget_draft=budget_draft,
                budget_final=budget_final,
                revenue_variance_draft=revenue_variance_draft,
                revenue_variance_final=revenue_variance_final,
                expense_variance_draft=expense_variance_draft,
                expense_variance_final=expense_variance_final
            )
            consolidated_years.append(consolidated_year)
        
        return ConsolidatedFinancialData(
            metadata={
                "version": "1.0.0",
                "last_updated": None,  # TODO: Set from file modification time
                "sources": ["audited", "budget"],
                "description": "Consolidated financial data from audited financial statements and budgets"
            },
            years=consolidated_years,
            years_available=all_years,
            latest_year=max(all_years) if all_years else None
        )
    
    def _save_consolidated_data(self):
        """Save consolidated data to cache file"""
        if self._cached_data:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self._cached_data.dict(), f, indent=2, default=str)
    
    def refresh_consolidated_data(self):
        """Refresh consolidated data by rebuilding from sources"""
        # Refresh audited source data
        self.audited_service.refresh_financial_data()
        
        # Rebuild consolidated data
        self._cached_data = self._build_consolidated_data()
        self._save_consolidated_data()
        return self._cached_data
    
    def add_budget_data(self, year: int, budget_data: BudgetData, is_final: bool = False):
        """Add or update budget data for a year"""
        consolidated_data = self.get_consolidated_data()
        year_data = consolidated_data.get_year(year)
        
        if not year_data:
            # Create new year data
            year_data = ConsolidatedFinancialYearData(year=year)
            consolidated_data.years.append(year_data)
            consolidated_data.years.sort(key=lambda x: x.year)
            consolidated_data.years_available = sorted([y.year for y in consolidated_data.years])
        
        # Update budget data
        if is_final:
            year_data.budget_final = budget_data
        else:
            year_data.budget_draft = budget_data
        
        # Recalculate variances
        self._recalculate_variances(year_data)
        
        # Save
        self._cached_data = consolidated_data
        self._save_consolidated_data()
    
    def _recalculate_variances(self, year_data: ConsolidatedFinancialYearData):
        """Recalculate budget variances for a year"""
        # Get actual values (prefer audited)
        actual_revenue = year_data.get_total_revenue()
        actual_expenses = year_data.get_total_expenses()
        
        # Calculate draft variances
        if year_data.budget_draft:
            if actual_revenue and year_data.budget_draft.total_revenue:
                year_data.revenue_variance_draft = actual_revenue - year_data.budget_draft.total_revenue
            if actual_expenses and year_data.budget_draft.total_expenses:
                year_data.expense_variance_draft = actual_expenses - year_data.budget_draft.total_expenses
        
        # Calculate final variances
        if year_data.budget_final:
            if actual_revenue and year_data.budget_final.total_revenue:
                year_data.revenue_variance_final = actual_revenue - year_data.budget_final.total_revenue
            if actual_expenses and year_data.budget_final.total_expenses:
                year_data.expense_variance_final = actual_expenses - year_data.budget_final.total_expenses
    
    def get_audited_financial_health_metrics(self) -> AuditedFinancialHealthMetrics:
        """Get audited financial health metrics from consolidated data (for backward compatibility)"""
        consolidated_data = self.get_consolidated_data()
        
        # Extract audited data
        audited_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                audited_years.append(year_data.audited)
        
        if not audited_years:
            raise ValueError("No audited financial data available")
        
        # Calculate trends
        revenue_trend = self._calculate_revenue_trends(audited_years)
        revenue_composition = self._calculate_revenue_composition(audited_years)
        
        return AuditedFinancialHealthMetrics(
            years=audited_years,
            revenue_trend=revenue_trend,
            revenue_composition=revenue_composition,
            latest_year=max([y.year for y in audited_years]),
            years_available=sorted([y.year for y in audited_years])
        )
    
    def _calculate_revenue_trends(self, years: List[AuditedFinancialYearData]) -> List[FinancialTrend]:
        """Calculate revenue trends from audited year data"""
        trends = []
        for i, year_data in enumerate(years):
            trend = FinancialTrend(
                year=year_data.year,
                revenue=year_data.total_revenue,
                expenses=year_data.total_expenses,
                net_income=year_data.net_income
            )
            
            # Calculate growth if we have previous year
            if i > 0:
                prev_year = years[i-1]
                if prev_year.total_revenue > 0:
                    trend.revenue_growth = ((year_data.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
                if prev_year.total_expenses > 0:
                    trend.expense_growth = ((year_data.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
            
            trends.append(trend)
        return trends
    
    def _calculate_revenue_composition(self, years: List[AuditedFinancialYearData]) -> List[RevenueComposition]:
        """Calculate revenue composition from audited year data"""
        return [
            RevenueComposition(
                year=year_data.year,
                program_services=year_data.program_service_revenue,
                contributions=year_data.contributions_grants,
                investment_income=year_data.investment_income,
                other_revenue=year_data.other_revenue
            )
            for year_data in years
        ]
    
    def get_audited_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary from audited data"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        
        if not audited_years:
            return {}
        
        latest_year = audited_years[-1]
        
        # Calculate growth rates
        revenue_growth = None
        expense_growth = None
        if len(audited_years) >= 2:
            prev_year = audited_years[-2]
            if prev_year.total_revenue > 0:
                revenue_growth = ((latest_year.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
            if prev_year.total_expenses > 0:
                expense_growth = ((latest_year.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
        
        return {
            "latest_year": latest_year.year,
            "previous_year": audited_years[-2].year if len(audited_years) >= 2 else None,
            "total_revenue": latest_year.total_revenue,
            "total_expenses": latest_year.total_expenses,
            "net_income": latest_year.net_income,
            "net_assets": latest_year.net_assets,
            "revenue_change": revenue_growth or 0,
            "expense_change": expense_growth or 0,
            "years_available": sorted([y.year for y in audited_years])
        }
    
    def get_audited_revenue_expense_trend_chart(self) -> FinancialChartData:
        """Get revenue vs expenses trend chart from audited data"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in audited_years]
        revenue_data = [year.total_revenue for year in audited_years]
        expense_data = [year.total_expenses for year in audited_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Total Revenue",
                    "data": revenue_data,
                    "borderColor": HL7_COLORS["success_green_alt"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Total Expenses",
                    "data": expense_data,
                    "borderColor": HL7_COLORS["brand_red_alt"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Revenue vs Expenses Trend"
        )
    
    def get_audited_revenue_composition_chart(self) -> FinancialChartData:
        """Get revenue composition chart from audited data"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in audited_years]
        program_services = [year.program_service_revenue for year in audited_years]
        contributions = [year.contributions_grants for year in audited_years]
        investment_income = [year.investment_income for year in audited_years]
        other_revenue = [year.other_revenue for year in audited_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "backgroundColor": HL7_COLORS["brand_red"],
                    "stack": "revenue"
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "backgroundColor": HL7_COLORS["warning_yellow"],
                    "stack": "revenue"
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "backgroundColor": HL7_COLORS["success_green"],
                    "stack": "revenue"
                },
                {
                    "label": "Other Revenue",
                    "data": other_revenue,
                    "backgroundColor": HL7_COLORS["neutral_gray"],
                    "stack": "revenue"
                }
            ],
            type="bar",
            title="Revenue Composition by Source (Raw)"
        )
    
    def get_audited_key_revenue_streams_chart(self) -> FinancialChartData:
        """Get key revenue streams chart from audited data"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in audited_years]
        program_services = [year.program_service_revenue for year in audited_years]
        contributions = [year.contributions_grants for year in audited_years]
        investment_income = [year.investment_income for year in audited_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "borderColor": HL7_COLORS["brand_red"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "borderColor": HL7_COLORS["warning_yellow"],
                    "backgroundColor": HL7_COLORS["warning_yellow_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "borderColor": HL7_COLORS["success_green"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Key Revenue Streams Over Time"
        )
    
    def get_audited_expense_breakdown_chart(self) -> FinancialChartData:
        """Get expense breakdown chart using new expense structure from Expenses tab"""
        # Use the same implementation as get_expense_breakdown_chart
        return self.get_expense_breakdown_chart()
    
    def get_audited_functional_expenses_chart(self) -> FinancialChartData:
        """Get functional expenses chart from audited data"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in audited_years]
        program_services = []
        supporting_services = []
        
        for year_data in audited_years:
            if year_data.functional_expenses:
                program_services.append(year_data.functional_expenses.total_program_services)
                supporting_services.append(year_data.functional_expenses.total_supporting_services)
            else:
                program_services.append(0.0)
                supporting_services.append(0.0)
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "backgroundColor": HL7_COLORS["brand_red"],
                    "stack": "expenses"
                },
                {
                    "label": "Supporting Services",
                    "data": supporting_services,
                    "backgroundColor": HL7_COLORS["neutral_gray"],
                    "stack": "expenses"
                }
            ],
            type="bar",
            title="Functional Expenses Breakdown"
        )
    
    def get_audited_detailed_functional_expenses_chart(self, service_type: str = "program") -> FinancialChartData:
        """
        Get detailed functional expenses chart from audited data using new expense structure
        service_type: "program" for Program Services, "supporting" for Supporting Services
        
        For Program Services, shows trends for:
        - Membership, Meetings & Education
        - Standards Development, PMO & Tooling
        - Federal Grant Projects
        
        For Supporting Services, shows trends for:
        - Management & General
        - Membership Development
        """
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return FinancialChartData(
                labels=[],
                datasets=[],
                type="line",
                title="Detailed Expense Trends - Program Services" if service_type == "program" else "Detailed Expense Trends - Supporting Services"
            )
        
        years = [str(year.year) for year in audited_years]
        
        # Initialize data arrays for each subcategory
        if service_type == "program":
            # Program Services subcategories
            membership_meetings_education_data = []
            standards_development_pmo_tooling_data = []
            federal_grant_projects_data = []
            
            for year_data in audited_years:
                if year_data.functional_expenses:
                    # Sum across all categories for each Program Services field
                    membership_meetings_education_total = 0.0
                    standards_development_pmo_tooling_total = 0.0
                    federal_grant_projects_total = 0.0
                    
                    for category in year_data.functional_expenses.categories:
                        cat_name_lower = category.category_name.lower().strip()
                        
                        # Skip invalid categories
                        if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                            continue
                        if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                            continue
                        if 'subtotal' in cat_name_lower:
                            continue
                        
                        # Sum the Program Services component fields across all categories
                        membership_meetings_education_total += round(category.membership_meetings_education or 0.0)
                        standards_development_pmo_tooling_total += round(category.standards_development_pmo_tooling or 0.0)
                        federal_grant_projects_total += round(category.federal_grant_projects or 0.0)
                    
                    membership_meetings_education_data.append(membership_meetings_education_total)
                    standards_development_pmo_tooling_data.append(standards_development_pmo_tooling_total)
                    federal_grant_projects_data.append(federal_grant_projects_total)
                else:
                    membership_meetings_education_data.append(0.0)
                    standards_development_pmo_tooling_data.append(0.0)
                    federal_grant_projects_data.append(0.0)
            
            datasets = []
            colors = [HL7_COLORS["brand_red"], HL7_COLORS["brand_red_alt"], HL7_COLORS["danger_orange"]]
            
            if any(v > 0 for v in membership_meetings_education_data):
                datasets.append({
                    "label": "Membership, Meetings & Education",
                    "data": membership_meetings_education_data,
                    "borderColor": colors[0],
                    "backgroundColor": colors[0] + "40",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                })
            
            if any(v > 0 for v in standards_development_pmo_tooling_data):
                datasets.append({
                    "label": "Standards Development, PMO & Tooling",
                    "data": standards_development_pmo_tooling_data,
                    "borderColor": colors[1],
                    "backgroundColor": colors[1] + "40",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                })
            
            if any(v > 0 for v in federal_grant_projects_data):
                datasets.append({
                    "label": "Federal Grant Projects",
                    "data": federal_grant_projects_data,
                    "borderColor": colors[2],
                    "backgroundColor": colors[2] + "40",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                })
        
        else:  # service_type == "supporting"
            # Supporting Services subcategories
            management_general_data = []
            membership_development_data = []
            
            for year_data in audited_years:
                if year_data.functional_expenses:
                    # Sum across all categories for each Supporting Services field
                    management_general_total = 0.0
                    membership_development_total = 0.0
                    
                    for category in year_data.functional_expenses.categories:
                        cat_name_lower = category.category_name.lower().strip()
                        
                        # Skip invalid categories
                        if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                            continue
                        if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                            continue
                        if 'subtotal' in cat_name_lower:
                            continue
                        
                        # Sum the Supporting Services component fields across all categories
                        management_general_total += round(category.management_general or 0.0)
                        membership_development_total += round(category.membership_development or 0.0)
                    
                    management_general_data.append(management_general_total)
                    membership_development_data.append(membership_development_total)
                else:
                    management_general_data.append(0.0)
                    membership_development_data.append(0.0)
            
            datasets = []
            colors = [HL7_COLORS["warning_yellow"], HL7_COLORS["danger_orange"]]
            
            if any(v > 0 for v in management_general_data):
                datasets.append({
                    "label": "Management & General",
                    "data": management_general_data,
                    "borderColor": colors[0],
                    "backgroundColor": colors[0] + "20",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "borderDash": [5, 5]
                })
            
            if any(v > 0 for v in membership_development_data):
                datasets.append({
                    "label": "Membership Development",
                    "data": membership_development_data,
                    "borderColor": colors[1],
                    "backgroundColor": colors[1] + "20",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "borderDash": [5, 5]
                })
        
        title = "Detailed Expense Trends - Program Services" if service_type == "program" else "Detailed Expense Trends - Supporting Services"
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="line",
            title=title
        )
    
    def get_financial_health_metrics(self) -> FinancialHealthMetrics:
        """Get financial health metrics from audited data (primary source) in FinancialHealthMetrics format"""
        consolidated_data = self.get_consolidated_data()
        
        # Extract audited data, convert to FinancialYearData format
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        if not financial_years:
            raise ValueError("No financial data available")
        
        # Calculate trends
        revenue_trend = self._calculate_financial_trends(financial_years)
        revenue_composition = self._calculate_financial_revenue_composition(financial_years)
        
        return FinancialHealthMetrics(
            years=financial_years,
            revenue_trend=revenue_trend,
            revenue_composition=revenue_composition,
            latest_year=max([y.year for y in financial_years]),
            years_available=sorted([y.year for y in financial_years])
        )
    
    def _calculate_financial_trends(self, years: List[FinancialYearData]) -> List[FinancialTrend]:
        """Calculate revenue trends from FinancialYearData"""
        trends = []
        for i, year_data in enumerate(years):
            trend = FinancialTrend(
                year=year_data.year,
                revenue=year_data.total_revenue,
                expenses=year_data.total_expenses,
                net_income=year_data.net_income
            )
            
            # Calculate growth if we have previous year
            if i > 0:
                prev_year = years[i-1]
                if prev_year.total_revenue > 0:
                    trend.revenue_growth = ((year_data.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
                if prev_year.total_expenses > 0:
                    trend.expense_growth = ((year_data.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
            
            trends.append(trend)
        return trends
    
    def _calculate_financial_revenue_composition(self, years: List[FinancialYearData]) -> List[RevenueComposition]:
        """Calculate revenue composition from FinancialYearData"""
        return [
            RevenueComposition(
                year=year_data.year,
                program_services=year_data.program_service_revenue,
                contributions=year_data.contributions_grants,
                investment_income=year_data.investment_income,
                other_revenue=year_data.other_revenue
            )
            for year_data in years
        ]
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary from audited data (primary source) - using actual audited data directly"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data - use audited data directly, not converted
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return {}
        
        latest_year = audited_years[-1]
        
        # Ensure values are calculated if missing (recalculate from components)
        # Total Revenue = Program Service Revenue + Federal Grants + Investment Income + Other Revenue + Net Assets Released
        if latest_year.total_revenue is None:
            latest_year.total_revenue = round(
                (latest_year.program_service_revenue or 0.0) +
                (latest_year.contributions_grants or 0.0) +
                (latest_year.investment_income or 0.0) +
                (latest_year.other_revenue or 0.0) +
                (latest_year.net_assets_released_from_restrictions or 0.0)
            )
        
        # Total Expenses = Program Services Expenses + Supporting Services Expenses
        if latest_year.total_expenses is None:
            # Try to calculate from component expense fields
            program_expenses = latest_year.total_program_services_expenses or 0.0
            supporting_expenses = latest_year.total_supporting_services_expenses or 0.0
            
            # If component totals not available, calculate from individual fields
            if program_expenses == 0.0:
                program_expenses = round(
                    (latest_year.membership_meetings_education_expenses or 0.0) +
                    (latest_year.standards_development_pmo_tooling_expenses or 0.0) +
                    (latest_year.federal_grant_projects_expenses or 0.0)
                )
            
            if supporting_expenses == 0.0:
                supporting_expenses = round(
                    (latest_year.management_general_expenses or 0.0) +
                    (latest_year.membership_development_expenses or 0.0)
                )
            
            latest_year.total_expenses = round(program_expenses + supporting_expenses)
        
        # Net Income = Total Revenue - Total Expenses
        if latest_year.net_income is None:
            latest_year.net_income = round((latest_year.total_revenue or 0.0) - (latest_year.total_expenses or 0.0))
        
        # Calculate growth rates and changes
        revenue_growth = None
        expense_growth = None
        net_income_change = None
        net_income_improvement = None
        assets_change = None
        
        if len(audited_years) >= 2:
            prev_year = audited_years[-2]
            
            # Ensure previous year values are also calculated
            if prev_year.total_revenue is None:
                prev_year.total_revenue = round(
                    (prev_year.program_service_revenue or 0.0) +
                    (prev_year.contributions_grants or 0.0) +
                    (prev_year.investment_income or 0.0) +
                    (prev_year.other_revenue or 0.0) +
                    (prev_year.net_assets_released_from_restrictions or 0.0)
                )
            
            if prev_year.total_expenses is None:
                program_exp = prev_year.total_program_services_expenses or 0.0
                supporting_exp = prev_year.total_supporting_services_expenses or 0.0
                
                if program_exp == 0.0:
                    program_exp = round(
                        (prev_year.membership_meetings_education_expenses or 0.0) +
                        (prev_year.standards_development_pmo_tooling_expenses or 0.0) +
                        (prev_year.federal_grant_projects_expenses or 0.0)
                    )
                
                if supporting_exp == 0.0:
                    supporting_exp = round(
                        (prev_year.management_general_expenses or 0.0) +
                        (prev_year.membership_development_expenses or 0.0)
                    )
                
                prev_year.total_expenses = round(program_exp + supporting_exp)
            
            if prev_year.net_income is None:
                prev_year.net_income = round((prev_year.total_revenue or 0.0) - (prev_year.total_expenses or 0.0))
            
            # Revenue growth
            if prev_year.total_revenue and prev_year.total_revenue > 0:
                revenue_growth = ((latest_year.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
            
            # Expense growth
            if prev_year.total_expenses and prev_year.total_expenses > 0:
                expense_growth = ((latest_year.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
            
            # Net income change
            latest_net_income = latest_year.net_income or 0.0
            prev_net_income = prev_year.net_income or 0.0
            net_income_change = latest_net_income - prev_net_income
            net_income_improvement = latest_net_income > prev_net_income
            
            # Net assets change
            if prev_year.net_assets and prev_year.net_assets != 0:
                assets_change = ((latest_year.net_assets - prev_year.net_assets) / abs(prev_year.net_assets)) * 100
            elif prev_year.net_assets == 0 and latest_year.net_assets:
                # Handle case where previous year was 0
                assets_change = 100.0 if latest_year.net_assets > 0 else -100.0 if latest_year.net_assets < 0 else 0.0
        
        return {
            "latest_year": latest_year.year,
            "previous_year": audited_years[-2].year if len(audited_years) >= 2 else None,
            "total_revenue": round(latest_year.total_revenue or 0.0),
            "total_expenses": round(latest_year.total_expenses or 0.0),
            "net_income": round(latest_year.net_income or 0.0),
            "net_assets": round(latest_year.net_assets or 0.0),
            "revenue_change": revenue_growth if revenue_growth is not None else 0.0,
            "expense_change": expense_growth if expense_growth is not None else 0.0,
            "net_income_change": net_income_change if net_income_change is not None else 0.0,
            "net_income_improvement": net_income_improvement if net_income_improvement is not None else False,
            "assets_change": assets_change if assets_change is not None else 0.0,
            "years_available": sorted([y.year for y in audited_years])
        }
    
    def get_revenue_expense_trend_chart(self) -> FinancialChartData:
        """Get revenue vs expenses trend chart from audited data (primary source)"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        financial_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in financial_years]
        revenue_data = [year.total_revenue for year in financial_years]
        expense_data = [year.total_expenses for year in financial_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Total Revenue",
                    "data": revenue_data,
                    "borderColor": HL7_COLORS["success_green_alt"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Total Expenses",
                    "data": expense_data,
                    "borderColor": HL7_COLORS["brand_red_alt"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Revenue vs Expenses Trend"
        )
    
    def get_revenue_composition_chart(self) -> FinancialChartData:
        """Get revenue composition chart from audited data (primary source)"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        financial_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in financial_years]
        program_services = [year.program_service_revenue for year in financial_years]
        contributions = [year.contributions_grants for year in financial_years]
        investment_income = [year.investment_income for year in financial_years]
        other_revenue = [year.other_revenue for year in financial_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "backgroundColor": HL7_COLORS["brand_red"],
                    "stack": "revenue"
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "backgroundColor": HL7_COLORS["warning_yellow"],
                    "stack": "revenue"
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "backgroundColor": HL7_COLORS["success_green"],
                    "stack": "revenue"
                },
                {
                    "label": "Other Revenue",
                    "data": other_revenue,
                    "backgroundColor": HL7_COLORS["neutral_gray"],
                    "stack": "revenue"
                }
            ],
            type="bar",
            title="Revenue Composition by Source (Raw)"
        )
    
    def get_revenue_composition_relative_chart(self) -> FinancialChartData:
        """Get revenue composition chart showing percentages (relative) from audited data"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        financial_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in financial_years]
        
        # Calculate percentages for each revenue source
        program_services_pct = []
        contributions_pct = []
        investment_income_pct = []
        other_revenue_pct = []
        
        for year in financial_years:
            total_revenue = year.total_revenue or 0.0
            if total_revenue > 0:
                program_services_pct.append(round(((year.program_service_revenue or 0.0) / total_revenue) * 100, 1))
                contributions_pct.append(round(((year.contributions_grants or 0.0) / total_revenue) * 100, 1))
                investment_income_pct.append(round(((year.investment_income or 0.0) / total_revenue) * 100, 1))
                other_revenue_pct.append(round(((year.other_revenue or 0.0) / total_revenue) * 100, 1))
            else:
                program_services_pct.append(0.0)
                contributions_pct.append(0.0)
                investment_income_pct.append(0.0)
                other_revenue_pct.append(0.0)
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services_pct,
                    "backgroundColor": HL7_COLORS["brand_red"],
                    "stack": "revenue"
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions_pct,
                    "backgroundColor": HL7_COLORS["warning_yellow"],
                    "stack": "revenue"
                },
                {
                    "label": "Investment Income",
                    "data": investment_income_pct,
                    "backgroundColor": HL7_COLORS["success_green"],
                    "stack": "revenue"
                },
                {
                    "label": "Other Revenue",
                    "data": other_revenue_pct,
                    "backgroundColor": HL7_COLORS["neutral_gray"],
                    "stack": "revenue"
                }
            ],
            type="bar",
            title="Revenue Composition by Source (Relative)"
        )
    
    def get_key_revenue_streams_chart(self) -> FinancialChartData:
        """Get key revenue streams chart from audited data (primary source)"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        financial_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in financial_years]
        program_services = [year.program_service_revenue for year in financial_years]
        contributions = [year.contributions_grants for year in financial_years]
        investment_income = [year.investment_income for year in financial_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "borderColor": HL7_COLORS["brand_red"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "borderColor": HL7_COLORS["warning_yellow"],
                    "backgroundColor": HL7_COLORS["warning_yellow_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "borderColor": HL7_COLORS["success_green"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Key Revenue Streams Over Time"
        )
    
    def get_expense_breakdown_chart(self) -> FinancialChartData:
        """Get expense breakdown chart using new expense structure from Expenses tab"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return FinancialChartData(
                labels=[],
                datasets=[],
                type="bar",
                title="Expense Breakdown"
            )
        
        years = [str(year.year) for year in audited_years]
        
        # Program Services Expenses subcategories
        membership_meetings_education_data = []
        standards_development_pmo_tooling_data = []
        federal_grant_projects_data = []
        
        # Supporting Services Expenses subcategories
        management_general_data = []
        membership_development_data = []
        
        for year_data in audited_years:
            # Program Services Expenses
            membership_meetings_education_data.append(
                round(year_data.membership_meetings_education_expenses or 0.0)
            )
            standards_development_pmo_tooling_data.append(
                round(year_data.standards_development_pmo_tooling_expenses or 0.0)
            )
            federal_grant_projects_data.append(
                round(year_data.federal_grant_projects_expenses or 0.0)
            )
            
            # Supporting Services Expenses
            management_general_data.append(
                round(year_data.management_general_expenses or 0.0)
            )
            membership_development_data.append(
                round(year_data.membership_development_expenses or 0.0)
            )
        
        datasets = []
        # Program Services colors (HL7 brand colors)
        program_colors = [HL7_COLORS["brand_red"], HL7_COLORS["brand_red_alt"], HL7_COLORS["danger_orange"]]
        # Supporting Services colors (HL7 brand colors)
        supporting_colors = [HL7_COLORS["warning_yellow"], HL7_COLORS["danger_orange"]]
        
        # Add Program Services datasets
        if any(v > 0 for v in membership_meetings_education_data):
            datasets.append({
                "label": "Membership, Meetings & Education",
                "data": membership_meetings_education_data,
                "backgroundColor": program_colors[0],
                "stack": "program_services"
            })
        
        if any(v > 0 for v in standards_development_pmo_tooling_data):
            datasets.append({
                "label": "Standards Development, PMO & Tooling",
                "data": standards_development_pmo_tooling_data,
                "backgroundColor": program_colors[1],
                "stack": "program_services"
            })
        
        if any(v > 0 for v in federal_grant_projects_data):
            datasets.append({
                "label": "Federal Grant Projects",
                "data": federal_grant_projects_data,
                "backgroundColor": program_colors[2],
                "stack": "program_services"
            })
        
        # Add Supporting Services datasets
        if any(v > 0 for v in management_general_data):
            datasets.append({
                "label": "Management & General",
                "data": management_general_data,
                "backgroundColor": supporting_colors[0],
                "stack": "supporting_services"
            })
        
        if any(v > 0 for v in membership_development_data):
            datasets.append({
                "label": "Membership Development",
                "data": membership_development_data,
                "backgroundColor": supporting_colors[1],
                "stack": "supporting_services"
            })
        
        # Fallback if no data available
        if not datasets:
            datasets = [
                {
                    "label": "Total Expenses",
                    "data": [round(year.total_expenses or 0.0) for year in audited_years],
                    "backgroundColor": HL7_COLORS["neutral_gray"],
                    "stack": "expenses"
                }
            ]
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="bar",
            title="Expense Breakdown"
        )
    
    def get_program_service_breakdown_chart(self) -> FinancialChartData:
        """Get program service revenue breakdown chart from audited data (primary source)"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data
        financial_years = []
        for year_data in consolidated_data.years:
            if year_data.audited:
                financial_years.append(_convert_audited_to_financial_year_data(year_data.audited))
        
        financial_years.sort(key=lambda x: x.year)
        
        years = [str(year.year) for year in financial_years]
        membership_dues = [year.membership_dues or 0 for year in financial_years]
        meetings = [year.meetings_conferences or 0 for year in financial_years]
        education = [year.education_certification or 0 for year in financial_years]
        project_management = [year.project_management_fees or 0 for year in financial_years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Membership Dues",
                    "data": membership_dues,
                    "borderColor": HL7_COLORS["brand_red"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Meetings & Conferences",
                    "data": meetings,
                    "borderColor": HL7_COLORS["warning_yellow"],
                    "backgroundColor": HL7_COLORS["warning_yellow_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Education & Certification",
                    "data": education,
                    "borderColor": HL7_COLORS["success_green"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Project Management Fees",
                    "data": project_management,
                    "borderColor": HL7_COLORS["danger_orange"],
                    "backgroundColor": HL7_COLORS["danger_orange_light"],
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Program Service Revenue Breakdown"
        )
    
    def get_revenue_expense_comparison_chart(self) -> FinancialChartData:
        """
        Get paired chart comparing Program Services Revenue vs Expenses by subcategory
        Shows revenue and expense bars side by side for each subcategory
        """
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return FinancialChartData(
                labels=[],
                datasets=[],
                type="bar",
                title="Program Services: Revenue vs Expenses Comparison"
            )
        
        years = [str(year.year) for year in audited_years]
        
        # Program Services Revenue subcategories
        membership_dues_revenue = []
        meetings_conferences_revenue = []
        education_certification_revenue = []
        project_management_fees_revenue = []
        other_program_services_revenue = []
        
        # Program Services Expenses subcategories (aggregated from functional expenses)
        membership_meetings_education_expenses = []
        standards_development_pmo_tooling_expenses = []
        federal_grant_projects_expenses = []
        
        for year_data in audited_years:
            # Revenue data
            membership_dues_revenue.append(round(year_data.membership_dues or 0.0))
            meetings_conferences_revenue.append(round(year_data.meetings_conferences or 0.0))
            education_certification_revenue.append(round(year_data.education_certification or 0.0))
            project_management_fees_revenue.append(round(year_data.project_management_fees or 0.0))
            other_program_services_revenue.append(round(year_data.other_program_services or 0.0))
            
            # Expense data - aggregate from functional expenses
            if year_data.functional_expenses:
                membership_meetings_education_total = 0.0
                standards_development_pmo_tooling_total = 0.0
                federal_grant_projects_total = 0.0
                
                for category in year_data.functional_expenses.categories:
                    cat_name_lower = category.category_name.lower().strip()
                    
                    # Skip invalid categories
                    if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                        continue
                    if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                        continue
                    if 'subtotal' in cat_name_lower:
                        continue
                    
                    membership_meetings_education_total += round(category.membership_meetings_education or 0.0)
                    standards_development_pmo_tooling_total += round(category.standards_development_pmo_tooling or 0.0)
                    federal_grant_projects_total += round(category.federal_grant_projects or 0.0)
                
                membership_meetings_education_expenses.append(membership_meetings_education_total)
                standards_development_pmo_tooling_expenses.append(standards_development_pmo_tooling_total)
                federal_grant_projects_expenses.append(federal_grant_projects_total)
            else:
                # Use direct expense fields if functional expenses not available
                membership_meetings_education_expenses.append(round(year_data.membership_meetings_education_expenses or 0.0))
                standards_development_pmo_tooling_expenses.append(round(year_data.standards_development_pmo_tooling_expenses or 0.0))
                federal_grant_projects_expenses.append(round(year_data.federal_grant_projects_expenses or 0.0))
        
        datasets = []
        
        # Revenue datasets (green tones)
        revenue_colors = [HL7_COLORS["success_green"], HL7_COLORS["success_green_alt"], HL7_COLORS["success_green"], HL7_COLORS["success_green_alt"], HL7_COLORS["success_green"]]
        if any(v > 0 for v in membership_dues_revenue):
            datasets.append({
                "label": "Membership Dues (Revenue)",
                "data": membership_dues_revenue,
                "backgroundColor": revenue_colors[0],
                "stack": "revenue_membership"
            })
        if any(v > 0 for v in meetings_conferences_revenue):
            datasets.append({
                "label": "Meetings & Conferences (Revenue)",
                "data": meetings_conferences_revenue,
                "backgroundColor": revenue_colors[1],
                "stack": "revenue_meetings"
            })
        if any(v > 0 for v in education_certification_revenue):
            datasets.append({
                "label": "Education & Certification (Revenue)",
                "data": education_certification_revenue,
                "backgroundColor": revenue_colors[2],
                "stack": "revenue_education"
            })
        if any(v > 0 for v in project_management_fees_revenue):
            datasets.append({
                "label": "Project Management Fees (Revenue)",
                "data": project_management_fees_revenue,
                "backgroundColor": revenue_colors[3],
                "stack": "revenue_pm"
            })
        if any(v > 0 for v in other_program_services_revenue):
            datasets.append({
                "label": "Other Program Services (Revenue)",
                "data": other_program_services_revenue,
                "backgroundColor": revenue_colors[4],
                "stack": "revenue_other"
            })
        
        # Expense datasets (red/orange tones)
        expense_colors = [HL7_COLORS["brand_red"], HL7_COLORS["danger_orange"], HL7_COLORS["warning_yellow"]]
        if any(v > 0 for v in membership_meetings_education_expenses):
            datasets.append({
                "label": "Membership, Meetings & Education (Expenses)",
                "data": membership_meetings_education_expenses,
                "backgroundColor": expense_colors[0],
                "stack": "expense_membership"
            })
        if any(v > 0 for v in standards_development_pmo_tooling_expenses):
            datasets.append({
                "label": "Standards Development, PMO & Tooling (Expenses)",
                "data": standards_development_pmo_tooling_expenses,
                "backgroundColor": expense_colors[1],
                "stack": "expense_standards"
            })
        if any(v > 0 for v in federal_grant_projects_expenses):
            datasets.append({
                "label": "Federal Grant Projects (Expenses)",
                "data": federal_grant_projects_expenses,
                "backgroundColor": expense_colors[2],
                "stack": "expense_grants"
            })
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="bar",
            title="Program Services: Revenue vs Expenses Comparison"
        )
    
    def get_program_services_revenue_expense_trend_chart(self) -> FinancialChartData:
        """
        Get line chart comparing total Program Services Revenue vs Expenses over time
        Shows green line for revenue and red line for expenses
        """
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return FinancialChartData(
                labels=[],
                datasets=[],
                type="line",
                title="Program Services: Revenue vs Expenses Trend"
            )
        
        years = [str(year.year) for year in audited_years]
        
        # Program Services Revenue (from audited data)
        program_services_revenue = []
        
        # Program Services Expenses (aggregated from functional expenses or direct field)
        program_services_expenses = []
        
        for year_data in audited_years:
            # Revenue
            program_services_revenue.append(round(year_data.program_service_revenue or 0.0))
            
            # Expenses - try to get from functional expenses first, then fallback to direct field
            if year_data.functional_expenses:
                # Aggregate from functional expenses
                total_program_expenses = 0.0
                for category in year_data.functional_expenses.categories:
                    cat_name_lower = category.category_name.lower().strip()
                    
                    # Skip invalid categories
                    if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                        continue
                    if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                        continue
                    if 'subtotal' in cat_name_lower:
                        continue
                    
                    # Sum all Program Services component fields
                    total_program_expenses += round(category.membership_meetings_education or 0.0)
                    total_program_expenses += round(category.standards_development_pmo_tooling or 0.0)
                    total_program_expenses += round(category.federal_grant_projects or 0.0)
                
                program_services_expenses.append(total_program_expenses)
            else:
                # Fallback to direct expense field or calculate from component fields
                if year_data.total_program_services_expenses is not None:
                    program_services_expenses.append(round(year_data.total_program_services_expenses))
                else:
                    # Calculate from component fields
                    total = round((year_data.membership_meetings_education_expenses or 0.0) +
                                 (year_data.standards_development_pmo_tooling_expenses or 0.0) +
                                 (year_data.federal_grant_projects_expenses or 0.0))
                    program_services_expenses.append(total)
        
        datasets = [
            {
                "label": "Program Services Revenue",
                "data": program_services_revenue,
                "borderColor": HL7_COLORS["success_green"],
                "backgroundColor": HL7_COLORS["success_green_light"],
                "fill": False,
                "tension": 0.4,
                "pointRadius": 5,
                "pointHoverRadius": 7,
                "borderWidth": 3
            },
            {
                "label": "Program Services Expenses",
                "data": program_services_expenses,
                "borderColor": HL7_COLORS["brand_red"],
                "backgroundColor": HL7_COLORS["brand_red_light"],
                "fill": False,
                "tension": 0.4,
                "pointRadius": 5,
                "pointHoverRadius": 7,
                "borderWidth": 3
            }
        ]
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="line",
            title="Program Services: Revenue vs Expenses Trend"
        )
    
    def get_detailed_financial_table(self) -> Dict[str, Any]:
        """Get detailed financial table from audited data (primary source) - using new data model"""
        consolidated_data = self.get_consolidated_data()
        
        # Get years with audited data - use audited data directly
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        # Filter to last 5 years
        recent_years = audited_years[-5:] if len(audited_years) >= 5 else audited_years
        
        if len(recent_years) < 2:
            return {"error": "Insufficient data for detailed table"}
        
        start_year = recent_years[0]
        end_year = recent_years[-1]
        year_span = end_year.year - start_year.year
        
        def calculate_percentage_change(start_value, end_value):
            if start_value == 0 or start_value is None:
                return 0
            return ((end_value - start_value) / abs(start_value)) * 100
        
        def get_program_services_expenses(year_data):
            """Get Program Services Expenses from functional expenses or direct fields"""
            if year_data.functional_expenses:
                total = 0.0
                for category in year_data.functional_expenses.categories:
                    cat_name_lower = category.category_name.lower().strip()
                    if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                        continue
                    if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                        continue
                    if 'subtotal' in cat_name_lower:
                        continue
                    total += round(category.membership_meetings_education or 0.0)
                    total += round(category.standards_development_pmo_tooling or 0.0)
                    total += round(category.federal_grant_projects or 0.0)
                return total
            else:
                return round(year_data.total_program_services_expenses or 
                           ((year_data.membership_meetings_education_expenses or 0.0) +
                            (year_data.standards_development_pmo_tooling_expenses or 0.0) +
                            (year_data.federal_grant_projects_expenses or 0.0)))
        
        def get_supporting_services_expenses(year_data):
            """Get Supporting Services Expenses from functional expenses or direct fields"""
            if year_data.functional_expenses:
                total = 0.0
                for category in year_data.functional_expenses.categories:
                    cat_name_lower = category.category_name.lower().strip()
                    if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                        continue
                    if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                        continue
                    if 'subtotal' in cat_name_lower:
                        continue
                    total += round(category.management_general or 0.0)
                    total += round(category.membership_development or 0.0)
                return total
            else:
                return round(year_data.total_supporting_services_expenses or
                           ((year_data.management_general_expenses or 0.0) +
                            (year_data.membership_development_expenses or 0.0)))
        
        table_data = {
            "years": [str(year.year) for year in recent_years],
            "year_span": f"{year_span}-YR CHANGE",
            "metrics": [
                {
                    "name": "Total Revenue",
                    "bold": False,
                    "values": [round(year.total_revenue or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_revenue, end_year.total_revenue)
                },
                {
                    "name": "Program Services Revenue",
                    "bold": False,
                    "values": [round(year.program_service_revenue or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.program_service_revenue, end_year.program_service_revenue)
                },
                {
                    "name": "Federal Grants and Contracts",
                    "bold": False,
                    "values": [round(year.contributions_grants or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.contributions_grants, end_year.contributions_grants)
                },
                {
                    "name": "Investment Income",
                    "bold": False,
                    "values": [round(year.investment_income or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.investment_income, end_year.investment_income)
                },
                {
                    "name": "Other Revenue",
                    "bold": False,
                    "values": [round(year.other_revenue or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.other_revenue, end_year.other_revenue)
                },
                {
                    "name": "Net Assets Released from Restrictions",
                    "bold": False,
                    "values": [round(year.net_assets_released_from_restrictions or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.net_assets_released_from_restrictions, end_year.net_assets_released_from_restrictions)
                },
                {
                    "name": "Total Expenses",
                    "bold": True,
                    "values": [round(year.total_expenses or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_expenses, end_year.total_expenses)
                },
                {
                    "name": "Program Services Expenses",
                    "bold": False,
                    "values": [get_program_services_expenses(year) for year in recent_years],
                    "change": calculate_percentage_change(get_program_services_expenses(start_year), get_program_services_expenses(end_year))
                },
                {
                    "name": "Supporting Services Expenses",
                    "bold": False,
                    "values": [get_supporting_services_expenses(year) for year in recent_years],
                    "change": calculate_percentage_change(get_supporting_services_expenses(start_year), get_supporting_services_expenses(end_year))
                },
                {
                    "name": "Net Income/(Loss)",
                    "bold": True,
                    "values": [round(year.net_income or 0.0) for year in recent_years],
                    "change": None
                },
                {
                    "name": "Net Assets",
                    "bold": True,
                    "values": [round(year.net_assets or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.net_assets, end_year.net_assets)
                },
                {
                    "name": "Total Assets",
                    "bold": True,
                    "values": [round(year.total_assets or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_assets, end_year.total_assets)
                },
                {
                    "name": "Total Liabilities",
                    "bold": True,
                    "values": [round(year.total_liabilities or 0.0) for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_liabilities, end_year.total_liabilities)
                }
            ]
        }
        
        return table_data
    
    def get_audited_detailed_financial_table(self) -> Dict[str, Any]:
        """Get detailed financial table from audited data - using new data model"""
        # Use the same implementation as get_detailed_financial_table
        return self.get_detailed_financial_table()
    
    def generate_llm_prompt(self) -> Dict[str, Any]:
        """Generate LLM prompt with financial data using new data model structure"""
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        prompt_lines = [
            "# HL7 International Financial Analysis Request",
            "",
            "## Organization Context",
            "HL7 International is a non-profit organization focused on healthcare interoperability standards.",
            "",
            "### Key Organizational Changes:",
            "- **April 2013**: **MAJOR BUSINESS MODEL CHANGE** - HL7 decided to make its standards, domain analysis models, profiles and implementation guides available at no cost to all. Previously, access to these standards required being an HL7 member. This date marks a substantial change in the HL7 business model and significantly impacts revenue analysis.",
            "- **2022**: Major restructuring - created two divisions (Standards Development and Standards Implementation) and hired three executives: Daniel Vreeman (Chief Standards Development Officer), Viet Nguyen (Chief Standards Implementation Officer), and Diego Kaminker (Deputy Chief Standards Implementation Officer)",
            "- **2023**: Purchased AMG LLC, which significantly impacted their financial structure as AMG staff became HL7 employees",
            "",
            "## Financial Data Analysis Request",
            "",
            "Please analyze the following financial data and provide a structured assessment with both positive developments and critical concerns. Format your response as markdown with two main sections:",
            "",
            "1. **Critical Financial Concerns** - Issues that need attention",
            "2. **Positive Developments** - Areas showing improvement or strength",
            "",
            "## Financial Data"
        ]
        
        if audited_years:
            year_range = f"({audited_years[0].year}-{audited_years[-1].year})"
            prompt_lines.append(f"## Financial Data {year_range}")
            prompt_lines.append("")
            prompt_lines.append("### Year-over-Year Summary")
            prompt_lines.append("")
            
            for year_data in audited_years:
                # Ensure values are calculated
                total_revenue = round(year_data.total_revenue or 0.0)
                total_expenses = round(year_data.total_expenses or 0.0)
                net_income = round(year_data.net_income or 0.0)
                net_assets = round(year_data.net_assets or 0.0)
                
                # Program Service Revenue breakdown
                program_service_revenue = round(year_data.program_service_revenue or 0.0)
                membership_dues = round(year_data.membership_dues or 0.0)
                membership_dues_org = round(year_data.membership_dues_organizational or 0.0)
                membership_dues_ind = round(year_data.membership_dues_individuals or 0.0)
                meetings_conferences = round(year_data.meetings_conferences or 0.0)
                education_certification = round(year_data.education_certification or 0.0)
                project_management_fees = round(year_data.project_management_fees or 0.0)
                other_program_services = round(year_data.other_program_services or 0.0)
                
                # Other revenue components
                contributions_grants = round(year_data.contributions_grants or 0.0)
                investment_income = round(year_data.investment_income or 0.0)
                other_revenue = round(year_data.other_revenue or 0.0)
                net_assets_released = round(year_data.net_assets_released_from_restrictions or 0.0)
                
                # Expense breakdown - get from functional expenses or direct fields
                def get_program_services_expenses(yd):
                    # First try direct fields (new structure)
                    if hasattr(yd, 'total_program_services_expenses') and yd.total_program_services_expenses:
                        return round(yd.total_program_services_expenses)
                    
                    # Try calculating from component fields
                    if (hasattr(yd, 'membership_meetings_education_expenses') and 
                        hasattr(yd, 'standards_development_pmo_tooling_expenses') and
                        hasattr(yd, 'federal_grant_projects_expenses')):
                        total = round((yd.membership_meetings_education_expenses or 0.0) +
                                     (yd.standards_development_pmo_tooling_expenses or 0.0) +
                                     (yd.federal_grant_projects_expenses or 0.0))
                        if total > 0:
                            return total
                    
                    # Try functional expenses with new structure
                    if yd.functional_expenses:
                        total = 0.0
                        for category in yd.functional_expenses.categories:
                            cat_name_lower = category.category_name.lower().strip()
                            if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                                continue
                            if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                                continue
                            if 'subtotal' in cat_name_lower:
                                continue
                            
                            # Try new structure fields first
                            if hasattr(category, 'membership_meetings_education'):
                                total += round(category.membership_meetings_education or 0.0)
                                total += round(category.standards_development_pmo_tooling or 0.0)
                                total += round(category.federal_grant_projects or 0.0)
                            # Fallback to old structure
                            elif hasattr(category, 'program_services'):
                                total += round(category.program_services or 0.0)
                        
                        if total > 0:
                            return total
                    
                    # Fallback: use total_program_services from functional expenses
                    if yd.functional_expenses and hasattr(yd.functional_expenses, 'total_program_services'):
                        return round(yd.functional_expenses.total_program_services or 0.0)
                    
                    return 0.0
                
                def get_supporting_services_expenses(yd):
                    # First try direct fields (new structure)
                    if hasattr(yd, 'total_supporting_services_expenses') and yd.total_supporting_services_expenses:
                        return round(yd.total_supporting_services_expenses)
                    
                    # Try calculating from component fields
                    if (hasattr(yd, 'management_general_expenses') and 
                        hasattr(yd, 'membership_development_expenses')):
                        total = round((yd.management_general_expenses or 0.0) +
                                     (yd.membership_development_expenses or 0.0))
                        if total > 0:
                            return total
                    
                    # Try functional expenses with new structure
                    if yd.functional_expenses:
                        total = 0.0
                        for category in yd.functional_expenses.categories:
                            cat_name_lower = category.category_name.lower().strip()
                            if 'total expenses' in cat_name_lower or cat_name_lower == 'total' or cat_name_lower == 'expenses':
                                continue
                            if 'for the year ended' in cat_name_lower or 'december' in cat_name_lower:
                                continue
                            if 'subtotal' in cat_name_lower:
                                continue
                            
                            # Try new structure fields first
                            if hasattr(category, 'management_general'):
                                total += round(category.management_general or 0.0)
                                total += round(category.membership_development or 0.0)
                            # Fallback to old structure
                            elif hasattr(category, 'supporting_services'):
                                total += round(category.supporting_services or 0.0)
                        
                        if total > 0:
                            return total
                    
                    # Fallback: use total_supporting_services from functional expenses
                    if yd.functional_expenses and hasattr(yd.functional_expenses, 'total_supporting_services'):
                        return round(yd.functional_expenses.total_supporting_services or 0.0)
                    
                    return 0.0
                
                program_services_expenses = get_program_services_expenses(year_data)
                supporting_services_expenses = get_supporting_services_expenses(year_data)
                
                prompt_lines.append(f"**{year_data.year}:**")
                prompt_lines.append(f"- Total Revenue: ${total_revenue:,}")
                prompt_lines.append(f"- Total Expenses: ${total_expenses:,}")
                prompt_lines.append(f"- Net Income: ${net_income:,}")
                prompt_lines.append(f"- Net Assets: ${net_assets:,}")
                prompt_lines.append(f"- Employees: {year_data.total_employees or 0}")
                prompt_lines.append(f"- Program Service Revenue: ${program_service_revenue:,}")
                prompt_lines.append(f"  - Membership Dues (Total): ${membership_dues:,}")
                if membership_dues_org > 0 or membership_dues_ind > 0:
                    prompt_lines.append(f"    - Membership Dues - Organizational: ${membership_dues_org:,}")
                    prompt_lines.append(f"    - Membership Dues - Individuals & Affiliates: ${membership_dues_ind:,}")
                prompt_lines.append(f"  - Meetings & Conferences: ${meetings_conferences:,}")
                prompt_lines.append(f"  - Education & Certification: ${education_certification:,}")
                prompt_lines.append(f"  - Project Management Fees: ${project_management_fees:,}")
                if other_program_services > 0:
                    prompt_lines.append(f"  - Other Program Services: ${other_program_services:,}")
                prompt_lines.append(f"- Federal Grants and Contracts: ${contributions_grants:,}")
                prompt_lines.append(f"- Investment Income: ${investment_income:,}")
                prompt_lines.append(f"- Other Revenue: ${other_revenue:,}")
                if net_assets_released > 0:
                    prompt_lines.append(f"- Net Assets Released from Restrictions: ${net_assets_released:,}")
                prompt_lines.append(f"- Program Services Expenses: ${program_services_expenses:,}")
                # Only show breakdown if direct fields exist
                if hasattr(year_data, 'membership_meetings_education_expenses'):
                    prompt_lines.append(f"  - Membership, Meetings & Education: ${round(year_data.membership_meetings_education_expenses or 0.0):,}")
                    prompt_lines.append(f"  - Standards Development, PMO & Tooling: ${round(year_data.standards_development_pmo_tooling_expenses or 0.0):,}")
                    prompt_lines.append(f"  - Federal Grant Projects: ${round(year_data.federal_grant_projects_expenses or 0.0):,}")
                prompt_lines.append(f"- Supporting Services Expenses: ${supporting_services_expenses:,}")
                # Only show breakdown if direct fields exist
                if hasattr(year_data, 'management_general_expenses'):
                    prompt_lines.append(f"  - Management & General: ${round(year_data.management_general_expenses or 0.0):,}")
                    prompt_lines.append(f"  - Membership Development: ${round(year_data.membership_development_expenses or 0.0):,}")
                prompt_lines.append("")
        
        # Add context and analysis requirements
        prompt_lines.extend([
            "",
            "## Key Context for Analysis",
            "",
            "### Major Business Model Change (April 2013)",
            "- **Critical Context**: In April 2013, HL7 made a fundamental change to its business model by making all standards freely available to everyone, not just members",
            "- **Revenue Impact**: This change likely had significant impact on membership value proposition and revenue streams",
            "- **Analysis Consideration**: When analyzing pre-2013 vs post-2013 data, consider how this change affected membership growth, retention, and alternative revenue development",
            "- **Strategic Context**: This change aligns with HL7's current 2025+ strategic vision for revenue diversification, as it represents an early move away from membership-dependent access models",
            "",
            "### AMG LLC Acquisition Impact (2023-2024)",
            "- In 2023, HL7 purchased AMG LLC for $3.3M in management services expenses",
            "- In 2024, AMG staff became HL7 employees, shifting from external management services to internal salaries",
            "- This structural change affects year-over-year comparisons",
            "- **Compensation Structure Impact**: The acquisition expanded the \"Officers, Directors, Trustees, Key Employees & Highest Compensated Employees\" category as former AMG executives and key personnel were integrated into HL7's leadership structure",
            "- **Growth Factors**: Recent increases in this compensation category reflect both executive pay growth and the addition of more senior roles from the AMG acquisition",
            "",
            "### Additional Operating Cost Factors (2023-2024)",
            "- **Financial Management Services**: HL7 brought on outside financial management services including a CFO/controller and 1.5 FTE accountant staff",
            "- **HR Services**: Hired Lemma Consulting for HR services",
            "- **Contractor Compensation**: These services are reported in the \"Total number of independent contractors who received more than $100,000 of compensation from the organization = 23\" category",
            "- **Cost Attribution**: While AMG acquisition is a significant factor, increased operating expenses also reflect strategic investments in financial management, HR services, and other professional services to support organizational growth",
            "",
            "### Revenue Streams Analysis",
            "- **Program Services Revenue** (primary revenue): Membership dues (with breakdown by Organizational vs Individuals & Affiliates), meetings, education, project management, other program services",
            "- **Federal Grants and Contracts**: Government funding",
            "- **Investment Income**: Market-dependent returns",
            "- **Other Revenue**: Miscellaneous sources",
            "- **Net Assets Released from Restrictions**: Assets released from donor restrictions",
            "",
            "### Expense Categories (New Structure)",
            "- **Program Services Expenses**:",
            "  - Membership, Meetings & Education",
            "  - Standards Development, PMO & Tooling",
            "  - Federal Grant Projects",
            "- **Supporting Services Expenses**:",
            "  - Management & General",
            "  - Membership Development",
            "",
            "### Functional Expenses",
            "Expenses are also tracked by functional category (e.g., Salaries and wages, Employee benefits, Professional fees, etc.) with breakdowns showing how much is allocated to Program Services vs Supporting Services.",
            "",
            "## 2025+ HL7 Strategic Vision: Revenue Diversification Strategies",
            "",
            "### Revenue Diversification Goals",
            "HL7 is actively working to develop initiatives that boost revenue from non-membership sources. This includes:",
            "- **Global Market Expansion**: Exploring new global markets and opportunities that align with HL7's mission and capabilities",
            "- **Channel Optimization**: Optimizing existing revenue channels for better performance",
            "- **New Partnership Development**: Building and securing new partnerships and collaborations that advance HL7's mission while creating additional revenue streams",
            "",
            "### New Market Offerings",
            "HL7 plans to develop a dedicated program to incubate and pilot new revenue-generating ideas and partnerships:",
            "- **Product Development**: Introducing new products, services, or offerings that address market needs",
            "- **Strategic Alignment**: Ensuring new offerings align with HL7's strategic goals and mission",
            "- **Innovation Pipeline**: Creating structured processes for evaluating and implementing new revenue opportunities",
            "",
            "### External Funding and Strategic Opportunities",
            "- **Funding Opportunity Capture**: Increasing the number of successful funding opportunities pursued and acquired",
            "- **Capability Building**: Developing processes for successful capture, including pipeline management, proposal development, and partnership strategies",
            "- **Strategic Opportunity Management**: Reducing instances where strategic opportunities are missed due to inability to capture them",
            "- **Structured Approach**: Developing systematic methods to secure strategic work",
            "",
            "### Strategic Impact",
            "By focusing on these diversification strategies, HL7 intends to:",
            "- **Strengthen Financial Foundation**: Enable growth and innovation while reducing reliance on membership dues",
            "- **Mission Support**: Support HL7's mission to improve health care standards globally",
            "- **Long-term Sustainability**: Create a more robust and diversified revenue model",
            "",
            "## Analysis Requirements",
            "",
            "Please provide insights on:",
            "",
            "1. **Financial Health Trends**: Multi-year patterns in revenue, expenses, and net income, with special attention to the impact of the April 2013 business model change",
            "2. **Revenue Diversification**: Stability and growth of different revenue streams, with specific attention to HL7's strategic goals for reducing reliance on membership dues and how the 2013 standards access change affected this. Include analysis of membership dues breakdown (Organizational vs Individuals & Affiliates) and Net Assets Released from Restrictions.",
            "3. **Expense Management**: Efficiency and cost control measures, including detailed analysis of Program Services Expenses vs Supporting Services Expenses, and how expenses are allocated across functional categories",
            "4. **Compensation Analysis**: Trends in executive and key personnel compensation, including the impact of the AMG acquisition on leadership structure and compensation levels, as well as strategic investments in financial management and HR services",
            "5. **Asset Management**: Net asset trends and financial stability",
            "6. **Business Model Evolution**: How the 2013 change to free standards access affected membership value proposition and revenue development over time",
            "7. **Strategic Implications**: Recommendations for financial sustainability that align with HL7's 2025+ strategic vision for revenue diversification",
            "8. **Strategic Alignment**: How current financial performance supports or challenges the organization's goals for new market offerings, partnerships, and external funding opportunities",
            "",
            "## Output Format",
            "",
            "**IMPORTANT: Your response must be formatted as a complete markdown file that can be saved directly as `financial_insights.md`.**",
            "",
            "Structure your response as a markdown document with the following format:",
            "",
            "```markdown",
            "# HL7 International Financial Analysis - 2024",
            "",
            "## Critical Financial Concerns",
            "",
            "### [Concern Title]",
            "- **Specific Issue**: [Detailed description with data points]",
            "- **Impact**: [Quantified impact with percentages and dollar amounts]",
            "- **Trend**: [Multi-year trend analysis with specific metrics]",
            "",
            "### [Another Concern Title]",
            "- **Specific Issue**: [Detailed description with data points]",
            "- **Impact**: [Quantified impact with percentages and dollar amounts]",
            "- **Trend**: [Multi-year trend analysis with specific metrics]",
            "",
            "## Positive Developments",
            "",
            "### [Positive Development Title]",
            "- **Achievement**: [Specific accomplishment with data points]",
            "- **Growth**: [Quantified growth with percentages and dollar amounts]",
            "- **Comparison**: [Year-over-year comparison with specific metrics]",
            "",
            "### [Another Positive Development Title]",
            "- **Achievement**: [Specific accomplishment with data points]",
            "- **Growth**: [Quantified growth with percentages and dollar amounts]",
            "- **Comparison**: [Year-over-year comparison with specific metrics]",
            "",
            "## Strategic Recommendations",
            "",
            "1. **[Revenue Diversification Recommendation]**: [Specific advice aligned with HL7's strategic vision for reducing membership dues reliance]",
            "2. **[Partnership & Funding Recommendation]**: [Specific advice for new partnerships and external funding opportunities]",
            "3. **[Market Development Recommendation]**: [Specific advice for new market offerings and global expansion]",
            "4. **[Financial Sustainability Recommendation]**: [Specific advice for long-term financial health and mission support]",
            "```",
            "",
            "**Formatting Requirements:**",
            "- Use proper markdown headers (`#`, `##`, `###`)",
            "- Use bullet points with `-` for lists",
            "- Use **bold text** for emphasis on key metrics",
            "- Include specific dollar amounts, percentages, and year-over-year comparisons",
            "- Focus on actionable insights valuable for organizational leadership",
            "- Ensure the output is a complete, standalone markdown document"
        ])
        
        prompt_text = "\n".join(prompt_lines)
        
        # Save to file
        prompt_file = Path("data/processed/llm_prompt.txt")
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompt_file, 'w') as f:
            f.write(prompt_text)
        
        return {
            "status": "success",
            "prompt_file": str(prompt_file),
            "message": "LLM prompt generated successfully"
        }
    
    def get_operating_reserve_chart(self) -> FinancialChartData:
        """
        Get operating reserve chart showing months of operating reserve over time
        Formula: Months of Operating Reserve = Unrestricted Net Assets / Average Monthly Expenses
        Target: 9 months
        """
        consolidated_data = self.get_consolidated_data()
        audited_years = [y.audited for y in consolidated_data.years if y.audited]
        audited_years.sort(key=lambda x: x.year)
        
        if not audited_years:
            return FinancialChartData(
                labels=[],
                datasets=[],
                type="line",
                title="Operating Reserve (Months)"
            )
        
        years = [str(year.year) for year in audited_years]
        
        # Calculate months of operating reserve for each year
        operating_reserve_months = []
        
        for year_data in audited_years:
            # Unrestricted Net Assets (using net_assets - note: fixed assets not separately tracked)
            unrestricted_net_assets = round(year_data.net_assets or 0.0)
            
            # Average Monthly Expenses = Total Expenses / 12
            total_expenses = round(year_data.total_expenses or 0.0)
            average_monthly_expenses = total_expenses / 12.0 if total_expenses > 0 else 0.0
            
            # Calculate months of operating reserve
            if average_monthly_expenses > 0:
                months = unrestricted_net_assets / average_monthly_expenses
                operating_reserve_months.append(round(months, 2))
            else:
                operating_reserve_months.append(0.0)
        
        # Target line (9 months)
        target_months = [9.0] * len(years)
        
        datasets = [
            {
                "label": "Operating Reserve (Months)",
                "data": operating_reserve_months,
                "borderColor": HL7_COLORS["brand_red"],
                "backgroundColor": HL7_COLORS["brand_red_light"],
                "fill": False,
                "tension": 0.4,
                "pointRadius": 5,
                "pointHoverRadius": 7,
                "borderWidth": 3
            },
            {
                "label": "Target (9 Months)",
                "data": target_months,
                "borderColor": HL7_COLORS["success_green"],
                "backgroundColor": HL7_COLORS["success_green_light"],
                "fill": False,
                "tension": 0,
                "pointRadius": 0,
                "pointHoverRadius": 0,
                "borderWidth": 2,
                "borderDash": [5, 5]
            }
        ]
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="line",
            title="Operating Reserve (Months)"
        )
    
    def get_budget_vs_actual_chart(self, year: Optional[int] = None) -> Dict[str, Any]:
        """Get chart data comparing budget vs actual for a year or all years"""
        consolidated_data = self.get_consolidated_data()
        
        if year:
            years_data = [consolidated_data.get_year(year)]
        else:
            years_data = consolidated_data.years
        
        # Filter to years with budget data
        years_with_budget = [y for y in years_data if y.budget_draft or y.budget_final]
        
        labels = [str(y.year) for y in years_with_budget]
        
        # Actual revenue from audited data
        actual_revenue = [y.get_total_revenue() or 0 for y in years_with_budget]
        
        # Budget revenue (prefer final over draft)
        budget_revenue = []
        for y in years_with_budget:
            if y.budget_final and y.budget_final.total_revenue:
                budget_revenue.append(y.budget_final.total_revenue)
            elif y.budget_draft and y.budget_draft.total_revenue:
                budget_revenue.append(y.budget_draft.total_revenue)
            else:
                budget_revenue.append(0)
        
        # Actual expenses from audited data
        actual_expenses = [y.get_total_expenses() or 0 for y in years_with_budget]
        
        # Budget expenses
        budget_expenses = []
        for y in years_with_budget:
            if y.budget_final and y.budget_final.total_expenses:
                budget_expenses.append(y.budget_final.total_expenses)
            elif y.budget_draft and y.budget_draft.total_expenses:
                budget_expenses.append(y.budget_draft.total_expenses)
            else:
                budget_expenses.append(0)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Actual Revenue",
                    "data": actual_revenue,
                    "borderColor": HL7_COLORS["success_green"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "fill": False,
                    "tension": 0.4
                },
                {
                    "label": "Budget Revenue",
                    "data": budget_revenue,
                    "borderColor": HL7_COLORS["success_green"],
                    "backgroundColor": HL7_COLORS["success_green_light"],
                    "borderDash": [5, 5],
                    "fill": False,
                    "tension": 0.4
                },
                {
                    "label": "Actual Expenses",
                    "data": actual_expenses,
                    "borderColor": HL7_COLORS["brand_red"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "fill": False,
                    "tension": 0.4
                },
                {
                    "label": "Budget Expenses",
                    "data": budget_expenses,
                    "borderColor": HL7_COLORS["brand_red"],
                    "backgroundColor": HL7_COLORS["brand_red_light"],
                    "borderDash": [5, 5],
                    "fill": False,
                    "tension": 0.4
                }
            ],
            "type": "line",
            "title": "Budget vs Actual"
        }
