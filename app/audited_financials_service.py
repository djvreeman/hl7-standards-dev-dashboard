import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.models import (
    AuditedFinancialHealthMetrics, AuditedFinancialYearData, FinancialTrend, 
    RevenueComposition, FinancialChartData, FunctionalExpensesData
)
from app.audited_financials_parser import AuditedFinancialsParser

class AuditedFinancialsService:
    """Service for managing financial data from audited financial statements"""
    
    def __init__(self, data_directory: str = "data/audited-financials", cache_file: str = "data/processed/audited_financial_data.json"):
        self.data_directory = data_directory
        self.cache_file = Path(cache_file)
        self.parser = AuditedFinancialsParser(data_directory)
        self._cached_data = None
    
    def get_financial_health_metrics(self) -> AuditedFinancialHealthMetrics:
        """Get financial health metrics, using cache if available"""
        if self._cached_data is None:
            self._load_financial_data()
        return self._cached_data
    
    def _load_financial_data(self):
        """Load financial data from cache or parse PDF files"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data_dict = json.load(f)
                self._cached_data = AuditedFinancialHealthMetrics(**data_dict)
                return
            except Exception as e:
                print(f"Error loading cached audited financial data: {e}")
        
        # Parse PDF files if cache doesn't exist or is invalid
        self._cached_data = self.parser.parse_all_statements()
        self._save_financial_data()
    
    def _save_financial_data(self):
        """Save financial data to cache file"""
        if self._cached_data:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self._cached_data.dict(), f, indent=2)
    
    def refresh_financial_data(self):
        """Refresh financial data by re-parsing PDF files (clears cache first)"""
        # Clear in-memory cache
        self._cached_data = None
        # Re-parse all PDF files
        self._cached_data = self.parser.parse_all_statements()
        # Save to cache file (overwrites existing cache)
        self._save_financial_data()
        return self._cached_data
    
    def get_revenue_expense_trend_chart(self) -> FinancialChartData:
        """Get chart data for revenue vs expenses trend"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        revenue_data = [year.total_revenue for year in metrics.years]
        expense_data = [year.total_expenses for year in metrics.years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Total Revenue",
                    "data": revenue_data,
                    "borderColor": "#0f8e48",  # HL7 Green
                    "backgroundColor": "rgba(15, 142, 72, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Total Expenses", 
                    "data": expense_data,
                    "borderColor": "#ec2227",  # HL7 Red
                    "backgroundColor": "rgba(236, 34, 39, 0.1)",
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
        """Get chart data for revenue composition by source"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        program_services = [year.program_service_revenue for year in metrics.years]
        contributions = [year.contributions_grants for year in metrics.years]
        investment_income = [year.investment_income for year in metrics.years]
        other_revenue = [year.other_revenue for year in metrics.years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "backgroundColor": "#dc2626",
                    "stack": "revenue"
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "backgroundColor": "#ca8a04",
                    "stack": "revenue"
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "backgroundColor": "#16a34a",
                    "stack": "revenue"
                },
                {
                    "label": "Other Revenue",
                    "data": other_revenue,
                    "backgroundColor": "#6b7280",
                    "stack": "revenue"
                }
            ],
            type="bar",
            title="Revenue Composition by Source"
        )
    
    def get_key_revenue_streams_chart(self) -> FinancialChartData:
        """Get chart data for key revenue streams over time"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        program_services = [year.program_service_revenue for year in metrics.years]
        contributions = [year.contributions_grants for year in metrics.years]
        investment_income = [year.investment_income for year in metrics.years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Program Services",
                    "data": program_services,
                    "borderColor": "#dc2626",
                    "backgroundColor": "rgba(220, 38, 38, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Federal Grants and Contracts",
                    "data": contributions,
                    "borderColor": "#ca8a04",
                    "backgroundColor": "rgba(202, 138, 4, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "borderColor": "#16a34a",
                    "backgroundColor": "rgba(22, 163, 74, 0.1)",
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
        """Get chart data for expense breakdown"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        salaries = [year.salaries_compensation for year in metrics.years]
        other_expenses = [year.other_expenses for year in metrics.years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Salaries & Compensation",
                    "data": salaries,
                    "backgroundColor": "#dc2626",
                    "stack": "expenses"
                },
                {
                    "label": "Other Expenses",
                    "data": other_expenses,
                    "backgroundColor": "#6b7280",
                    "stack": "expenses"
                }
            ],
            type="bar",
            title="Expense Breakdown"
        )
    
    def get_functional_expenses_chart(self) -> FinancialChartData:
        """Get chart data for functional expenses breakdown (Program Services vs Supporting Services)"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        program_services = []
        supporting_services = []
        
        for year_data in metrics.years:
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
                    "backgroundColor": "#16a34a",  # Green for program services
                    "stack": "functional"
                },
                {
                    "label": "Supporting Services",
                    "data": supporting_services,
                    "backgroundColor": "#dc2626",  # Red for supporting services
                    "stack": "functional"
                }
            ],
            type="bar",
            title="Functional Expenses: Program Services vs Supporting Services"
        )
    
    def get_detailed_functional_expenses_chart(self) -> FinancialChartData:
        """Get detailed chart showing expense categories by function as a line plot"""
        metrics = self.get_financial_health_metrics()
        
        # Collect all unique expense categories across all years
        all_categories = set()
        for year_data in metrics.years:
            if year_data.functional_expenses:
                for category in year_data.functional_expenses.categories:
                    all_categories.add(category.category_name)
        
        all_categories = sorted(list(all_categories))
        years = [str(year.year) for year in metrics.years]
        
        # Create datasets for each category showing Program Services and Supporting Services
        datasets = []
        colors = [
            "#dc2626", "#6b7280", "#16a34a", "#ca8a04", "#ea580c",
            "#5f9baf", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b",
            "#6366f1", "#ef4444", "#84cc16", "#f97316", "#8b5a2b",
            "#06b6d4", "#8b5cf6", "#f43f5e", "#14b8a6", "#f59e0b"
        ]
        
        for i, category_name in enumerate(all_categories):
            program_data = []
            supporting_data = []
            
            for year_data in metrics.years:
                if year_data.functional_expenses:
                    category = next(
                        (cat for cat in year_data.functional_expenses.categories if cat.category_name == category_name),
                        None
                    )
                    if category:
                        # Ensure non-negative values
                        program_data.append(max(0.0, category.program_services))
                        supporting_data.append(max(0.0, category.supporting_services))
                    else:
                        program_data.append(0.0)
                        supporting_data.append(0.0)
                else:
                    program_data.append(0.0)
                    supporting_data.append(0.0)
            
            # Only include categories that have non-zero values
            if any(v > 0 for v in program_data + supporting_data):
                color = colors[i % len(colors)]
                datasets.append({
                    "label": f"{category_name} - Program Services",
                    "data": program_data,
                    "borderColor": color,
                    "backgroundColor": color + "40",  # Add transparency
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                })
                datasets.append({
                    "label": f"{category_name} - Supporting Services",
                    "data": supporting_data,
                    "borderColor": color + "80",  # Lighter version
                    "backgroundColor": color + "20",  # More transparency
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "borderDash": [5, 5]  # Dashed line to distinguish from program services
                })
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="line",
            title="Detailed Functional Expenses by Category"
        )
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary statistics"""
        metrics = self.get_financial_health_metrics()
        latest_year = metrics.years[-1] if metrics.years else None
        
        if not latest_year:
            return {}
        
        # Calculate growth rates
        revenue_growth = None
        expense_growth = None
        if len(metrics.years) >= 2:
            prev_year = metrics.years[-2]
            if prev_year.total_revenue > 0:
                revenue_growth = ((latest_year.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
            if prev_year.total_expenses > 0:
                expense_growth = ((latest_year.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
        
        # Calculate additional trend metrics
        net_income_change = 0
        assets_change = 0
        net_income_improvement = False
        
        if len(metrics.years) >= 2:
            prev_year = metrics.years[-2]
            net_income_change = latest_year.net_income - prev_year.net_income
            if prev_year.net_assets > 0:
                assets_change = ((latest_year.net_assets - prev_year.net_assets) / prev_year.net_assets) * 100
            if latest_year.net_income > prev_year.net_income:
                net_income_improvement = True
        
        return {
            "latest_year": latest_year.year,
            "previous_year": metrics.years[-2].year if len(metrics.years) >= 2 else None,
            "total_revenue": latest_year.total_revenue,
            "total_expenses": latest_year.total_expenses,
            "net_income": latest_year.net_income,
            "net_assets": latest_year.net_assets,
            "revenue_change": revenue_growth or 0,
            "expense_change": expense_growth or 0,
            "net_income_change": net_income_change,
            "assets_change": assets_change,
            "net_income_improvement": net_income_improvement,
            "years_available": metrics.years_available
        }
    
    def get_detailed_financial_table(self) -> Dict[str, Any]:
        """Get detailed financial data for table display (last 5 years)"""
        metrics = self.get_financial_health_metrics()
        
        # Filter to last 5 years
        recent_years = metrics.years[-5:] if len(metrics.years) >= 5 else metrics.years
        recent_years.sort(key=lambda x: x.year)
        
        if len(recent_years) < 2:
            return {"error": "Insufficient data for detailed table"}
        
        # Calculate change from first to last year in the range
        start_year = recent_years[0]
        end_year = recent_years[-1]
        year_span = end_year.year - start_year.year
        
        def calculate_percentage_change(start_value, end_value):
            if start_value == 0:
                return 0
            return ((end_value - start_value) / abs(start_value)) * 100
        
        # Build table data
        table_data = {
            "years": [str(year.year) for year in recent_years],
            "year_span": f"{year_span}-YR CHANGE",
            "metrics": [
                {
                    "name": "Total Revenue",
                    "bold": False,
                    "values": [year.total_revenue for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_revenue, end_year.total_revenue)
                },
                {
                    "name": "Program Services",
                    "bold": False,
                    "values": [year.program_service_revenue for year in recent_years],
                    "change": calculate_percentage_change(start_year.program_service_revenue, end_year.program_service_revenue)
                },
                {
                    "name": "Federal Grants and Contracts",
                    "bold": False,
                    "values": [year.contributions_grants for year in recent_years],
                    "change": calculate_percentage_change(start_year.contributions_grants, end_year.contributions_grants)
                },
                {
                    "name": "Investment Income",
                    "bold": False,
                    "values": [year.investment_income for year in recent_years],
                    "change": calculate_percentage_change(start_year.investment_income, end_year.investment_income)
                },
                {
                    "name": "Other Revenue",
                    "bold": False,
                    "values": [year.other_revenue for year in recent_years],
                    "change": calculate_percentage_change(start_year.other_revenue, end_year.other_revenue)
                },
                {
                    "name": "Total Expenses",
                    "bold": True,
                    "values": [year.total_expenses for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_expenses, end_year.total_expenses)
                },
                {
                    "name": "Salaries/Compensation",
                    "bold": False,
                    "values": [year.salaries_compensation for year in recent_years],
                    "change": calculate_percentage_change(start_year.salaries_compensation, end_year.salaries_compensation)
                },
                {
                    "name": "Net Income/(Loss)",
                    "bold": True,
                    "values": [year.net_income for year in recent_years],
                    "change": None
                },
                {
                    "name": "Net Assets",
                    "bold": True,
                    "values": [year.net_assets for year in recent_years],
                    "change": calculate_percentage_change(start_year.net_assets, end_year.net_assets)
                },
                {
                    "name": "Total Assets",
                    "bold": True,
                    "values": [year.total_assets for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_assets, end_year.total_assets)
                },
                {
                    "name": "Total Liabilities",
                    "bold": True,
                    "values": [year.total_liabilities for year in recent_years],
                    "change": calculate_percentage_change(start_year.total_liabilities, end_year.total_liabilities)
                }
            ]
        }
        
        return table_data

