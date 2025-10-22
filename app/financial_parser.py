import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from app.models import FinancialYearData, FinancialHealthMetrics, FinancialTrend, RevenueComposition

logger = logging.getLogger(__name__)

class Form990Parser:
    """Parser for IRS Form 990 XML files"""
    
    def __init__(self, data_directory: str = "data/990s"):
        self.data_directory = Path(data_directory)
        self.namespace = {"efile": "http://www.irs.gov/efile"}
    
    def parse_all_forms(self) -> FinancialHealthMetrics:
        """Parse all 990 forms in the data directory"""
        financial_data = []
        years_available = []
        
        # Get all XML files and sort by year
        xml_files = sorted(self.data_directory.glob("*.xml"))
        
        for xml_file in xml_files:
            try:
                year_data = self.parse_single_form(xml_file)
                if year_data:
                    financial_data.append(year_data)
                    years_available.append(year_data.year)
            except Exception as e:
                logger.error(f"Error parsing {xml_file}: {e}")
                continue
        
        if not financial_data:
            raise ValueError("No valid 990 forms found")
        
        # Sort by year
        financial_data.sort(key=lambda x: x.year)
        years_available.sort()
        
        # Calculate trends
        revenue_trend = self._calculate_trends(financial_data)
        revenue_composition = self._calculate_revenue_composition(financial_data)
        
        return FinancialHealthMetrics(
            years=financial_data,
            revenue_trend=revenue_trend,
            revenue_composition=revenue_composition,
            latest_year=max(years_available),
            years_available=years_available
        )
    
    def parse_single_form(self, xml_file: Path) -> Optional[FinancialYearData]:
        """Parse a single 990 form XML file"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Extract year from filename or XML
            year = self._extract_year(xml_file, root)
            
            # Find the IRS990 element
            irs990 = root.find(".//efile:IRS990", self.namespace)
            if irs990 is None:
                logger.warning(f"No IRS990 element found in {xml_file}")
                return None
            
            # Extract financial data
            year_data = self._extract_financial_data(irs990, year)
            return year_data
            
        except Exception as e:
            logger.error(f"Error parsing {xml_file}: {e}")
            return None
    
    def _extract_year(self, xml_file: Path, root: ET.Element) -> int:
        """Extract year from filename or XML"""
        # Try to get year from filename first
        filename = xml_file.stem
        if filename.startswith("20"):
            return int(filename[:4])
        
        # Fallback to XML data
        tax_yr = root.find(".//efile:TaxYr", self.namespace)
        if tax_yr is not None and tax_yr.text:
            return int(tax_yr.text)
        
        raise ValueError(f"Could not determine year for {xml_file}")
    
    def _extract_financial_data(self, irs990: ET.Element, year: int) -> FinancialYearData:
        """Extract financial data from IRS990 element"""
        
        def get_amount(element_name: str, default: float = 0.0) -> float:
            """Helper to extract amount from XML element"""
            element = irs990.find(f".//efile:{element_name}", self.namespace)
            if element is not None and element.text:
                try:
                    # Values are already in dollars in 990 XML
                    return float(element.text)
                except ValueError:
                    pass
            return default
        
        def get_int(element_name: str, default: int = 0) -> int:
            """Helper to extract integer from XML element"""
            element = irs990.find(f".//efile:{element_name}", self.namespace)
            if element is not None and element.text:
                try:
                    return int(element.text)
                except ValueError:
                    pass
            return default
        
        # Basic financial data
        total_revenue = get_amount("CYTotalRevenueAmt")
        total_expenses = get_amount("CYTotalExpensesAmt")
        net_income = total_revenue - total_expenses
        
        # Revenue breakdown
        program_service_revenue = get_amount("CYProgramServiceRevenueAmt")
        contributions_grants = get_amount("CYContributionsGrantsAmt")
        investment_income = get_amount("CYInvestmentIncomeAmt")
        other_revenue = get_amount("CYOtherRevenueAmt")
        
        # Expense breakdown
        salaries_compensation = get_amount("CYSalariesCompEmpBnftPaidAmt")
        other_expenses = get_amount("CYOtherExpensesAmt")
        
        # Management services (pre-2024) - this was the AMG LLC expense
        management_services = None
        if year < 2024:
            # Look for management services in other expenses or as a separate line
            # This might need adjustment based on actual XML structure
            management_services = get_amount("CYManagementAndGeneralExpensesAmt", 0.0)
            if management_services == 0:
                # Try alternative field names
                management_services = get_amount("CYTotalManagementAndGeneralExpensesAmt", 0.0)
        
        # Balance sheet data
        total_assets = get_amount("TotalAssetsEOYAmt")
        total_liabilities = get_amount("TotalLiabilitiesEOYAmt")
        net_assets = get_amount("NetAssetsOrFundBalancesEOYAmt")
        
        # Employee data
        total_employees = get_int("TotalEmployeeCnt")
        total_volunteers = get_int("TotalVolunteersCnt")
        
        # Program service revenue breakdown - extract from ProgramServiceRevenueGrp
        membership_dues = None
        meetings_conferences = None
        education_certification = None
        project_management_fees = None
        qualified_sponsorship_payments = None
        other_program_services = None
        
        # Extract detailed program service revenue breakdown
        program_service_groups = irs990.findall(".//efile:ProgramServiceRevenueGrp", self.namespace)
        for group in program_service_groups:
            desc_element = group.find("efile:Desc", self.namespace)
            amount_element = group.find("efile:TotalRevenueColumnAmt", self.namespace)
            
            if desc_element is not None and amount_element is not None:
                description = desc_element.text.lower()
                amount = float(amount_element.text) if amount_element.text else 0.0
                
                # Handle various label formats over the years
                if "member dues" in description or "membership dues" in description:
                    membership_dues = amount
                elif "meetings" in description or "conferences" in description or "conferences & meetings" in description:
                    meetings_conferences = amount
                elif "education" in description or "certification" in description or "education fees" in description:
                    education_certification = amount
                elif "project management" in description:
                    project_management_fees = amount
                elif "sponsorship" in description:
                    qualified_sponsorship_payments = amount
                # Note: Other categories like "DAVINCIN PROJECT", "ONC GRANT", "ARGONAUGT PROJECT" 
                # are not mapped to specific fields as they appear to be one-time or special projects
        
        # Calculate other program services as the difference between total and mapped categories
        mapped_total = (membership_dues or 0) + (meetings_conferences or 0) + (education_certification or 0) + (project_management_fees or 0) + (qualified_sponsorship_payments or 0)
        if mapped_total < program_service_revenue:
            other_program_services = program_service_revenue - mapped_total
        
        return FinancialYearData(
            year=year,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_income=net_income,
            program_service_revenue=program_service_revenue,
            contributions_grants=contributions_grants,
            investment_income=investment_income,
            other_revenue=other_revenue,
            membership_dues=membership_dues,
            meetings_conferences=meetings_conferences,
            education_certification=education_certification,
            project_management_fees=project_management_fees,
            qualified_sponsorship_payments=qualified_sponsorship_payments,
            other_program_services=other_program_services,
            salaries_compensation=salaries_compensation,
            other_expenses=other_expenses,
            management_services=management_services,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_assets=net_assets,
            total_employees=total_employees,
            total_volunteers=total_volunteers
        )
    
    def _calculate_trends(self, financial_data: List[FinancialYearData]) -> List[FinancialTrend]:
        """Calculate revenue and expense trends"""
        trends = []
        
        for i, year_data in enumerate(financial_data):
            revenue_growth = None
            expense_growth = None
            
            if i > 0:
                prev_year = financial_data[i-1]
                if prev_year.total_revenue > 0:
                    revenue_growth = ((year_data.total_revenue - prev_year.total_revenue) / prev_year.total_revenue) * 100
                if prev_year.total_expenses > 0:
                    expense_growth = ((year_data.total_expenses - prev_year.total_expenses) / prev_year.total_expenses) * 100
            
            trends.append(FinancialTrend(
                year=year_data.year,
                revenue=year_data.total_revenue,
                expenses=year_data.total_expenses,
                net_income=year_data.net_income,
                revenue_growth=revenue_growth,
                expense_growth=expense_growth
            ))
        
        return trends
    
    def _calculate_revenue_composition(self, financial_data: List[FinancialYearData]) -> List[RevenueComposition]:
        """Calculate revenue composition by source"""
        composition = []
        
        for year_data in financial_data:
            composition.append(RevenueComposition(
                year=year_data.year,
                program_services=year_data.program_service_revenue,
                contributions=year_data.contributions_grants,
                investment_income=year_data.investment_income,
                other_revenue=year_data.other_revenue
            ))
        
        return composition
