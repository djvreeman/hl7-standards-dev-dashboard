"""
Service for managing the single consolidated financial data file with editing capabilities
"""
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from app.models import (
    ConsolidatedFinancialData, ConsolidatedFinancialYearData,
    AuditedFinancialYearData, BudgetData, FunctionalExpenseCategory,
    FunctionalExpensesData, BudgetFunctionalExpenseCategory
)

class FinancialDataEditorService:
    """Service for managing and editing the single consolidated financial data file"""
    
    def __init__(self, data_file: str = "data/processed/financial_data_consolidated.json"):
        self.data_file = Path(data_file)
        self._cached_data: Optional[ConsolidatedFinancialData] = None
    
    def load_data(self) -> ConsolidatedFinancialData:
        """Load financial data from the single consolidated file"""
        if self._cached_data is None:
            self._load_from_file()
        return self._cached_data
    
    def _load_from_file(self):
        """Load data from JSON file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data_dict = json.load(f)
                self._cached_data = ConsolidatedFinancialData(**data_dict)
            except Exception as e:
                raise ValueError(f"Error loading financial data: {e}")
        else:
            # Create empty structure
            self._cached_data = ConsolidatedFinancialData(
                metadata={
                    "version": "2.0.0",
                    "last_updated": datetime.now().isoformat(),
                    "description": "Single consolidated financial data file with manual overrides"
                },
                years=[],
                years_available=[],
                latest_year=None
            )
            self.save_data()
    
    def save_data(self):
        """Save data to JSON file"""
        if self._cached_data:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            # Update metadata
            self._cached_data.metadata["last_updated"] = datetime.now().isoformat()
            with open(self.data_file, 'w') as f:
                json.dump(self._cached_data.dict(), f, indent=2, default=str)
    
    def get_year_data(self, year: int) -> Optional[ConsolidatedFinancialYearData]:
        """Get data for a specific year"""
        data = self.load_data()
        return data.get_year(year)
    
    def create_or_update_year(self, year: int, year_data: Dict[str, Any]) -> ConsolidatedFinancialYearData:
        """Create or update year data"""
        data = self.load_data()
        existing_year = data.get_year(year)
        
        # Parse the incoming data
        audited_data = None
        if year_data.get("audited"):
            audited_data = AuditedFinancialYearData(**year_data["audited"])
        
        budget_draft = None
        if year_data.get("budget_draft"):
            budget_draft = BudgetData(**year_data["budget_draft"])
        
        budget_final = None
        if year_data.get("budget_final"):
            budget_final = BudgetData(**year_data["budget_final"])
        
        # Calculate variances
        revenue_variance_draft = None
        revenue_variance_final = None
        expense_variance_draft = None
        expense_variance_final = None
        
        if audited_data:
            if budget_draft:
                if audited_data.total_revenue and budget_draft.total_revenue:
                    revenue_variance_draft = audited_data.total_revenue - budget_draft.total_revenue
                if audited_data.total_expenses and budget_draft.total_expenses:
                    expense_variance_draft = audited_data.total_expenses - budget_draft.total_expenses
            if budget_final:
                if audited_data.total_revenue and budget_final.total_revenue:
                    revenue_variance_final = audited_data.total_revenue - budget_final.total_revenue
                if audited_data.total_expenses and budget_final.total_expenses:
                    expense_variance_final = audited_data.total_expenses - budget_final.total_expenses
        
        updated_year = ConsolidatedFinancialYearData(
            year=year,
            audited=audited_data,
            budget_draft=budget_draft,
            budget_final=budget_final,
            revenue_variance_draft=revenue_variance_draft,
            revenue_variance_final=revenue_variance_final,
            expense_variance_draft=expense_variance_draft,
            expense_variance_final=expense_variance_final
        )
        
        # Update or add year
        if existing_year:
            # Update existing
            for i, y in enumerate(data.years):
                if y.year == year:
                    data.years[i] = updated_year
                    break
        else:
            # Add new year
            data.years.append(updated_year)
            data.years_available = sorted([y.year for y in data.years])
            if data.latest_year is None or year > data.latest_year:
                data.latest_year = year
        
        self._cached_data = data
        self.save_data()
        return updated_year
    
    def update_audited_field(self, year: int, field_name: str, value: Optional[float]) -> ConsolidatedFinancialYearData:
        """Update a single audited field"""
        data = self.load_data()
        year_data = data.get_year(year)
        
        # Round value to nearest whole number (nearest dollar)
        rounded_value = round(value) if value is not None else None
        
        if not year_data:
            # Create new year with audited data
            # Get default values for required fields
            audited_dict = {
                "year": year,
                "total_revenue": 0.0,
                "total_expenses": 0.0,
                "net_income": 0.0,
                "program_service_revenue": 0.0,
                "contributions_grants": 0.0,
                "investment_income": 0.0,
                "other_revenue": 0.0,
                "salaries_compensation": 0.0,
                "other_expenses": 0.0,
                "total_assets": 0.0,
                "total_liabilities": 0.0,
                "net_assets": 0.0,
                "total_employees": 0,
                "total_volunteers": 0,
                "total_program_services_expenses": 0.0,
                "total_supporting_services_expenses": 0.0
            }
            audited_dict[field_name] = rounded_value if rounded_value is not None else 0.0
            audited_data = AuditedFinancialYearData(**audited_dict)
            year_data = ConsolidatedFinancialYearData(year=year, audited=audited_data)
            data.years.append(year_data)
            data.years_available = sorted([y.year for y in data.years])
            if data.latest_year is None or year > data.latest_year:
                data.latest_year = year
        elif not year_data.audited:
            # Create audited data for existing year
            # Get default values for required fields
            audited_dict = {
                "year": year,
                "total_revenue": 0.0,
                "total_expenses": 0.0,
                "net_income": 0.0,
                "program_service_revenue": 0.0,
                "contributions_grants": 0.0,
                "investment_income": 0.0,
                "other_revenue": 0.0,
                "salaries_compensation": 0.0,
                "other_expenses": 0.0,
                "total_assets": 0.0,
                "total_liabilities": 0.0,
                "net_assets": 0.0,
                "total_employees": 0,
                "total_volunteers": 0,
                "total_program_services_expenses": 0.0,
                "total_supporting_services_expenses": 0.0
            }
            audited_dict[field_name] = rounded_value if rounded_value is not None else 0.0
            year_data.audited = AuditedFinancialYearData(**audited_dict)
        else:
            # Update existing audited data
            # Only update if the field exists in the model
            if hasattr(year_data.audited, field_name):
                setattr(year_data.audited, field_name, rounded_value if rounded_value is not None else 0.0)
            else:
                raise ValueError(f"Field '{field_name}' does not exist in AuditedFinancialYearData")
        
        # Recalculate Membership Dues (Total) if component fields changed
        membership_dues_changed = False
        if field_name in ["membership_dues_organizational", "membership_dues_individuals"]:
            membership_dues_total = round(
                (year_data.audited.membership_dues_organizational or 0) +
                (year_data.audited.membership_dues_individuals or 0)
            )
            year_data.audited.membership_dues = membership_dues_total
            membership_dues_changed = True
        
        # Recalculate Program Service Revenue if component fields changed
        program_service_revenue_changed = False
        if membership_dues_changed or field_name in ["membership_dues", "meetings_conferences", "education_certification", "project_management_fees", "other_program_services"]:
            program_service_revenue = round(
                (year_data.audited.membership_dues or 0) +
                (year_data.audited.meetings_conferences or 0) +
                (year_data.audited.education_certification or 0) +
                (year_data.audited.project_management_fees or 0) +
                (year_data.audited.other_program_services or 0)
            )
            year_data.audited.program_service_revenue = program_service_revenue
            program_service_revenue_changed = True
        
        # Recalculate Total Revenue if component fields changed (including when program_service_revenue was recalculated)
        if program_service_revenue_changed or field_name in ["program_service_revenue", "contributions_grants", "investment_income", "other_revenue", "net_assets_released_from_restrictions"]:
            total_revenue = round(
                (year_data.audited.program_service_revenue or 0) +
                (year_data.audited.contributions_grants or 0) +
                (year_data.audited.investment_income or 0) +
                (year_data.audited.other_revenue or 0) +
                (year_data.audited.net_assets_released_from_restrictions or 0)
            )
            year_data.audited.total_revenue = total_revenue
        
        # Recalculate Program Services Expenses if component fields changed
        program_services_expenses_changed = False
        if field_name in ["membership_meetings_education_expenses", "standards_development_pmo_tooling_expenses", "federal_grant_projects_expenses"]:
            total_program_services_expenses = round(
                (year_data.audited.membership_meetings_education_expenses or 0) +
                (year_data.audited.standards_development_pmo_tooling_expenses or 0) +
                (year_data.audited.federal_grant_projects_expenses or 0)
            )
            year_data.audited.total_program_services_expenses = total_program_services_expenses
            program_services_expenses_changed = True
        
        # Recalculate Supporting Services Expenses if component fields changed
        supporting_services_expenses_changed = False
        if field_name in ["management_general_expenses", "membership_development_expenses"]:
            total_supporting_services_expenses = round(
                (year_data.audited.management_general_expenses or 0) +
                (year_data.audited.membership_development_expenses or 0)
            )
            year_data.audited.total_supporting_services_expenses = total_supporting_services_expenses
            supporting_services_expenses_changed = True
        
        # Recalculate Total Expenses if component fields changed
        if program_services_expenses_changed or supporting_services_expenses_changed or field_name in ["total_program_services_expenses", "total_supporting_services_expenses"]:
            total_expenses = round(
                (year_data.audited.total_program_services_expenses or 0) +
                (year_data.audited.total_supporting_services_expenses or 0)
            )
            year_data.audited.total_expenses = total_expenses
        
        # Recalculate net_income if revenue or expenses changed (rounded)
        if field_name in ["total_revenue", "total_expenses"] or program_services_expenses_changed or supporting_services_expenses_changed:
            if year_data.audited.total_revenue is not None and year_data.audited.total_expenses is not None:
                year_data.audited.net_income = round(year_data.audited.total_revenue - year_data.audited.total_expenses)
        
        # Update variances (rounded)
        if year_data.audited:
            if year_data.budget_draft:
                if year_data.audited.total_revenue and year_data.budget_draft.total_revenue:
                    year_data.revenue_variance_draft = round(year_data.audited.total_revenue - year_data.budget_draft.total_revenue)
                if year_data.audited.total_expenses and year_data.budget_draft.total_expenses:
                    year_data.expense_variance_draft = round(year_data.audited.total_expenses - year_data.budget_draft.total_expenses)
            if year_data.budget_final:
                if year_data.audited.total_revenue and year_data.budget_final.total_revenue:
                    year_data.revenue_variance_final = round(year_data.audited.total_revenue - year_data.budget_final.total_revenue)
                if year_data.audited.total_expenses and year_data.budget_final.total_expenses:
                    year_data.expense_variance_final = round(year_data.audited.total_expenses - year_data.budget_final.total_expenses)
        
        self._cached_data = data
        self.save_data()
        return year_data
    
    def update_budget_field(self, year: int, budget_version: str, field_name: str, value: Optional[float]) -> ConsolidatedFinancialYearData:
        """Update a single budget field (draft or final)"""
        data = self.load_data()
        year_data = data.get_year(year)
        
        # Round value to nearest whole number (nearest dollar)
        rounded_value = round(value) if value is not None else None
        
        if not year_data:
            year_data = ConsolidatedFinancialYearData(year=year)
            data.years.append(year_data)
        
        if budget_version == "draft":
            if not year_data.budget_draft:
                year_data.budget_draft = BudgetData(year=year, version="draft")
            setattr(year_data.budget_draft, field_name, rounded_value)
        elif budget_version == "final":
            if not year_data.budget_final:
                year_data.budget_final = BudgetData(year=year, version="final")
            setattr(year_data.budget_final, field_name, rounded_value)
        
        # Recalculate variances (rounded)
        if year_data.audited:
            if year_data.budget_draft:
                if year_data.audited.total_revenue and year_data.budget_draft.total_revenue:
                    year_data.revenue_variance_draft = round(year_data.audited.total_revenue - year_data.budget_draft.total_revenue)
                if year_data.audited.total_expenses and year_data.budget_draft.total_expenses:
                    year_data.expense_variance_draft = round(year_data.audited.total_expenses - year_data.budget_draft.total_expenses)
            if year_data.budget_final:
                if year_data.audited.total_revenue and year_data.budget_final.total_revenue:
                    year_data.revenue_variance_final = round(year_data.audited.total_revenue - year_data.budget_final.total_revenue)
                if year_data.audited.total_expenses and year_data.budget_final.total_expenses:
                    year_data.expense_variance_final = round(year_data.audited.total_expenses - year_data.budget_final.total_expenses)
        
        self._cached_data = data
        self.save_data()
        return year_data
    
    def update_functional_expense_category(self, year: int, category_name: str, 
                                         program_services: Optional[float] = None,
                                         supporting_services: Optional[float] = None,
                                         total: Optional[float] = None,
                                         membership_meetings_education: Optional[float] = None,
                                         standards_development_pmo_tooling: Optional[float] = None,
                                         federal_grant_projects: Optional[float] = None,
                                         management_general: Optional[float] = None,
                                         membership_development: Optional[float] = None) -> ConsolidatedFinancialYearData:
        """Update a functional expense category with new structure matching audited financials"""
        data = self.load_data()
        year_data = data.get_year(year)
        
        # Round values to nearest whole number (nearest dollar)
        rounded_membership_meetings_education = round(membership_meetings_education) if membership_meetings_education is not None else None
        rounded_standards_development_pmo_tooling = round(standards_development_pmo_tooling) if standards_development_pmo_tooling is not None else None
        rounded_federal_grant_projects = round(federal_grant_projects) if federal_grant_projects is not None else None
        rounded_management_general = round(management_general) if management_general is not None else None
        rounded_membership_development = round(membership_development) if membership_development is not None else None
        
        # Legacy fields for backward compatibility
        rounded_program = round(program_services) if program_services is not None else None
        rounded_supporting = round(supporting_services) if supporting_services is not None else None
        rounded_total = round(total) if total is not None else None
        
        if not year_data or not year_data.audited:
            raise ValueError(f"No audited data found for year {year}")
        
        if not year_data.audited.functional_expenses:
            year_data.audited.functional_expenses = FunctionalExpensesData(
                year=year,
                categories=[],
                total_program_services=0.0,
                total_supporting_services=0.0,
                total_expenses=0.0
            )
        
        # Find or create category
        category = None
        for cat in year_data.audited.functional_expenses.categories:
            if cat.category_name == category_name:
                category = cat
                break
        
        if not category:
            category = FunctionalExpenseCategory(
                category_name=category_name,
                membership_meetings_education=0.0,
                standards_development_pmo_tooling=0.0,
                federal_grant_projects=0.0,
                management_general=0.0,
                membership_development=0.0
            )
            year_data.audited.functional_expenses.categories.append(category)
        
        # Update new structure fields
        if rounded_membership_meetings_education is not None:
            category.membership_meetings_education = rounded_membership_meetings_education
        if rounded_standards_development_pmo_tooling is not None:
            category.standards_development_pmo_tooling = rounded_standards_development_pmo_tooling
        if rounded_federal_grant_projects is not None:
            category.federal_grant_projects = rounded_federal_grant_projects
        if rounded_management_general is not None:
            category.management_general = rounded_management_general
        if rounded_membership_development is not None:
            category.membership_development = rounded_membership_development
        
        # Recalculate auto-calculated fields
        category.program_services_total = round(
            (category.membership_meetings_education or 0.0) +
            (category.standards_development_pmo_tooling or 0.0) +
            (category.federal_grant_projects or 0.0)
        )
        category.supporting_services_total = round(
            (category.management_general or 0.0) +
            (category.membership_development or 0.0)
        )
        category.total = round(
            (category.program_services_total or 0.0) +
            (category.supporting_services_total or 0.0)
        )
        
        # Legacy field updates for backward compatibility
        if rounded_program is not None:
            category.program_services = rounded_program
        if rounded_supporting is not None:
            category.supporting_services = rounded_supporting
        if rounded_total is not None:
            category.total = rounded_total
        
        # Recalculate functional expenses totals (rounded)
        year_data.audited.functional_expenses.total_program_services = round(sum(
            (cat.program_services_total or cat.program_services or 0.0) 
            for cat in year_data.audited.functional_expenses.categories
        ))
        year_data.audited.functional_expenses.total_supporting_services = round(sum(
            (cat.supporting_services_total or cat.supporting_services or 0.0) 
            for cat in year_data.audited.functional_expenses.categories
        ))
        year_data.audited.functional_expenses.total_expenses = round(
            year_data.audited.functional_expenses.total_program_services +
            year_data.audited.functional_expenses.total_supporting_services
        )
        
        self._cached_data = data
        self.save_data()
        return year_data
    
    def get_editable_data_structure(self) -> Dict[str, Any]:
        """Get data in a structure optimized for editing UI"""
        data = self.load_data()
        
        # Get all unique categories across all years
        all_categories = set()
        for year_data in data.years:
            if year_data.audited and year_data.audited.functional_expenses:
                for cat in year_data.audited.functional_expenses.categories:
                    all_categories.add(cat.category_name)
        
        all_categories = sorted(list(all_categories))
        
        # Build structure for UI
        result = {
            "years": [],
            "categories": all_categories,
            "revenue_fields": [
                "total_revenue",
                "program_service_revenue",
                "contributions_grants",
                "investment_income",
                "other_revenue",
                "membership_dues",
                "meetings_conferences",
                "education_certification",
                "project_management_fees"
            ],
            "expense_fields": [
                "total_expenses",
                "salaries_compensation",
                "other_expenses"
            ],
            "balance_sheet_fields": [
                "total_assets",
                "total_liabilities",
                "net_assets"
            ]
        }
        
        for year_data in sorted(data.years, key=lambda x: x.year):
            year_dict = {
                "year": year_data.year,
                "audited": {},
                "budget_draft": {},
                "budget_final": {},
                "functional_expenses": {}
            }
            
            if year_data.audited:
                audited_dict = year_data.audited.dict()
                year_dict["audited"] = {k: v for k, v in audited_dict.items() if k != "functional_expenses"}
                
                if year_data.audited.functional_expenses:
                    for cat in year_data.audited.functional_expenses.categories:
                        year_dict["functional_expenses"][cat.category_name] = {
                            "program_services": cat.program_services,
                            "supporting_services": cat.supporting_services,
                            "total": cat.total
                        }
            
            if year_data.budget_draft:
                year_dict["budget_draft"] = year_data.budget_draft.dict()
            
            if year_data.budget_final:
                year_dict["budget_final"] = year_data.budget_final.dict()
            
            result["years"].append(year_dict)
        
        return result
    
    def import_from_audited_service(self):
        """Import data from AuditedFinancialsService (one-time import from PDFs)"""
        from app.audited_financials_service import AuditedFinancialsService
        audited_service = AuditedFinancialsService()
        # Refresh to ensure we get the latest parsed data with all fields (including new membership breakdown fields)
        audited_metrics = audited_service.refresh_financial_data()
        
        data = self.load_data()
        
        # Add or update years from audited service
        for audited_year in audited_metrics.years:
            existing_year = data.get_year(audited_year.year)
            
            if existing_year:
                # Update existing year's audited data
                existing_year.audited = audited_year
            else:
                # Create new year
                new_year = ConsolidatedFinancialYearData(
                    year=audited_year.year,
                    audited=audited_year,
                    budget_draft=None,
                    budget_final=None
                )
                data.years.append(new_year)
        
        # Update metadata
        data.years_available = sorted([y.year for y in data.years])
        data.latest_year = max(data.years_available) if data.years_available else None
        
        self._cached_data = data
        self.save_data()
        return data

