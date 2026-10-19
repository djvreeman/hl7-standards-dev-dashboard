import pdfplumber
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from app.models import (
    AuditedFinancialYearData, AuditedFinancialHealthMetrics, FinancialTrend, 
    RevenueComposition, FunctionalExpensesData, FunctionalExpenseCategory
)

logger = logging.getLogger(__name__)

class AuditedFinancialsParser:
    """Parser for audited financial statements PDF files"""
    
    def __init__(self, data_directory: str = "data/audited-financials"):
        self.data_directory = Path(data_directory)
        self.tolerance = 1000.0  # Tolerance for validation checks (in dollars)
    
    def parse_all_statements(self) -> AuditedFinancialHealthMetrics:
        """Parse all audited financial statements in the data directory"""
        financial_data_dict = {}  # Use dict to avoid duplicates by year
        years_available = []
        
        # Get all PDF files and sort by filename
        pdf_files = sorted(self.data_directory.glob("*.pdf"))
        
        for pdf_file in pdf_files:
            try:
                year_data_list = self.parse_single_statement(pdf_file)
                for year_data in year_data_list:
                    if year_data:
                        # Only keep the most recent data for each year (in case of duplicates)
                        if year_data.year not in financial_data_dict:
                            financial_data_dict[year_data.year] = year_data
                            years_available.append(year_data.year)
                        else:
                            # If duplicate, prefer data with more complete functional expenses breakdown
                            # This is important because multi-year PDFs often only show totals, not breakdowns
                            existing = financial_data_dict[year_data.year]
                            
                            # Check functional expenses completeness
                            existing_has_func_exp = existing.functional_expenses is not None
                            new_has_func_exp = year_data.functional_expenses is not None
                            
                            if new_has_func_exp and not existing_has_func_exp:
                                # New data has functional expenses, existing doesn't - prefer new
                                financial_data_dict[year_data.year] = year_data
                            elif existing_has_func_exp and not new_has_func_exp:
                                # Existing has functional expenses, new doesn't - keep existing
                                pass
                            elif new_has_func_exp and existing_has_func_exp:
                                # Both have functional expenses - check which has more complete breakdown
                                existing_cat_count = len(existing.functional_expenses.categories) if existing.functional_expenses else 0
                                new_cat_count = len(year_data.functional_expenses.categories) if year_data.functional_expenses else 0
                                
                                # Count categories with actual program/supporting breakdown (not just totals)
                                existing_has_breakdown = sum(1 for cat in existing.functional_expenses.categories if cat.program_services > 0 or cat.supporting_services > 0) if existing.functional_expenses else 0
                                new_has_breakdown = sum(1 for cat in year_data.functional_expenses.categories if cat.program_services > 0 or cat.supporting_services > 0) if year_data.functional_expenses else 0
                                
                                # Prefer data with more categories that have actual breakdown (program/supporting amounts)
                                if new_has_breakdown > existing_has_breakdown:
                                    financial_data_dict[year_data.year] = year_data
                                elif existing_has_breakdown > new_has_breakdown:
                                    pass  # Keep existing
                                elif new_cat_count > existing_cat_count:
                                    financial_data_dict[year_data.year] = year_data
                                elif year_data.total_revenue > existing.total_revenue:
                                    # If breakdowns are similar, prefer higher revenue (more recent/complete data)
                                    financial_data_dict[year_data.year] = year_data
                            else:
                                # Neither has functional expenses - prefer higher revenue
                                if year_data.total_revenue > existing.total_revenue:
                                    financial_data_dict[year_data.year] = year_data
                                elif year_data.total_revenue == existing.total_revenue:
                                    # If revenues are equal, check completeness
                                    existing_completeness = sum(1 for v in [existing.total_revenue, existing.total_expenses, existing.total_assets, existing.net_assets] if v > 0)
                                    new_completeness = sum(1 for v in [year_data.total_revenue, year_data.total_expenses, year_data.total_assets, year_data.net_assets] if v > 0)
                                    if new_completeness > existing_completeness:
                                        financial_data_dict[year_data.year] = year_data
            except Exception as e:
                logger.error(f"Error parsing {pdf_file}: {e}")
                continue
        
        if not financial_data_dict:
            raise ValueError("No valid audited financial statements found")
        
        # Convert dict to sorted list
        financial_data = sorted(financial_data_dict.values(), key=lambda x: x.year)
        years_available = sorted(list(set(years_available)))
        
        # Calculate trends
        revenue_trend = self._calculate_trends(financial_data)
        revenue_composition = self._calculate_revenue_composition(financial_data)
        
        return AuditedFinancialHealthMetrics(
            years=financial_data,
            revenue_trend=revenue_trend,
            revenue_composition=revenue_composition,
            latest_year=max(years_available),
            years_available=years_available
        )
    
    def parse_single_statement(self, pdf_file) -> List[AuditedFinancialYearData]:
        """Parse a single audited financial statement PDF file"""
        year_data_list = []
        
        try:
            pdf_path = Path(pdf_file) if not isinstance(pdf_file, Path) else pdf_file
            with pdfplumber.open(pdf_path) as pdf:
                # Extract text from all pages
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
                
                # Extract years from filename or text, and identify primary year
                years, primary_year = self._extract_years(pdf_path, full_text)
                
                # Parse primary year first (source of truth), then other years
                years_to_parse = [primary_year] + [y for y in years if y != primary_year] if primary_year else years
                
                for year in years_to_parse:
                    year_data = self._extract_financial_data(full_text, year, pdf)
                    if year_data:
                        year_data_list.append(year_data)
        
        except Exception as e:
            logger.error(f"Error parsing {pdf_file}: {e}")
            return []
        
        return year_data_list
    
    def _extract_years(self, pdf_file: Path, text: str) -> Tuple[List[int], Optional[int]]:
        """Extract years from filename or text, returning list of years and the primary/current year"""
        years = []
        primary_year = None
        
        # Try to extract from filename first
        filename = pdf_file.stem
        year_matches = re.findall(r'20\d{2}', filename)
        if year_matches:
            years = [int(y) for y in year_matches]
            # If multiple years, the highest year is the current/primary year
            if len(years) > 1:
                primary_year = max(years)
            else:
                primary_year = years[0]
        
        # If filename has "and" or ranges, handle them
        if "and" in filename.lower() or "-" in filename:
            # Look for patterns like "2020 and 2021" or "2020-2021"
            range_matches = re.findall(r'(\d{4})\s*(?:and|-)\s*(\d{4})', filename)
            if range_matches:
                years = []
                for start, end in range_matches:
                    start_year = int(start)
                    end_year = int(end)
                    years.extend([start_year, end_year])
                    # The later year is the current/primary year
                    primary_year = max(start_year, end_year)
        
        # Fallback to text search
        if not years:
            # Look for "For the year ended December 31, YYYY" or "For the years ended December 31, YYYY and YYYY"
            # The pattern "For the year ended December 31, 2024 with comparable totals for 2023" means 2024 is primary
            single_year_match = re.search(r'For the year ended December 31, (\d{4})', text, re.IGNORECASE)
            if single_year_match:
                primary_year = int(single_year_match.group(1))
                years = [primary_year]
                # Check if there's a "with comparable totals for" clause
                comparable_match = re.search(r'with comparable totals for (\d{4})', text, re.IGNORECASE)
                if comparable_match:
                    years.append(int(comparable_match.group(1)))
            else:
                # Look for "For the years ended December 31, YYYY and YYYY"
                multi_year_match = re.search(r'For the years ended December 31, (\d{4})\s+and\s+(\d{4})', text, re.IGNORECASE)
                if multi_year_match:
                    year1 = int(multi_year_match.group(1))
                    year2 = int(multi_year_match.group(2))
                    years = [year1, year2]
                    # The first year mentioned is typically the current year
                    primary_year = year1
                else:
                    # Fallback patterns
                    year_patterns = [
                        r'year\s+ended\s+[A-Za-z]+\s+\d{1,2},\s+(\d{4})',
                        r'for\s+the\s+year\s+ended\s+[A-Za-z]+\s+\d{1,2},\s+(\d{4})',
                        r'(\d{4})\s+and\s+(\d{4})',
                    ]
                    for pattern in year_patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            if isinstance(matches[0], tuple):
                                years = [int(y) for match in matches for y in match]
                            else:
                                years = [int(m) for m in matches]
                            if years:
                                primary_year = max(years)
                            break
        
        # Remove duplicates and sort, but prioritize primary year
        years = sorted(list(set(years)))
        
        # If we have multiple years and no primary identified, use the highest year
        if not primary_year and years:
            primary_year = max(years)
        elif not primary_year:
            primary_year = years[0] if years else None
        
        if not years:
            raise ValueError(f"Could not determine years for {pdf_file}")
        
        return years, primary_year
    
    def _extract_financial_data(self, text: str, year: int, pdf) -> Optional[AuditedFinancialYearData]:
        """Extract financial data for a specific year from the text"""
        try:
            # Extract Statement of Financial Position data
            balance_sheet_data = self._parse_statement_of_financial_position(text, year)

            # Extract Statement of Activities data
            activities_data = self._parse_statement_of_activities(text, year)

            # Parse functional expenses table - try table extraction first, then text parsing
            functional_expenses = None
            # Try to extract tables from PDF pages
            tables = []
            try:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
            except:
                pass
            
            # Try table-based parsing first (more reliable for structured tables)
            if tables:
                functional_expenses = self._parse_functional_expenses_table(text, year, tables)
            
            # Fall back to text-based parsing if table parsing didn't work
            if not functional_expenses or len(functional_expenses.categories) < 3:
                functional_expenses = self._parse_statement_of_functional_expenses(text, year)
            
            # Combine data (values already rounded by _parse_amount)
            total_revenue = activities_data.get('total_revenues', 0.0)
            total_expenses = activities_data.get('total_expenses', 0.0)
            net_income = round(total_revenue - total_expenses)
            
            # Revenue breakdown
            membership_dues_org = activities_data.get('membership_dues_org', 0.0)
            membership_dues_ind = activities_data.get('membership_dues_ind', 0.0)
            membership_dues = membership_dues_org + membership_dues_ind
            meetings_conferences = activities_data.get('meetings', 0.0)
            education_certification = activities_data.get('education_certification', 0.0)
            project_management_fees = activities_data.get('project_management_fees', 0.0)
            contributions_grants = activities_data.get('federal_grants_contracts', 0.0)
            investment_income = activities_data.get('investment_return', 0.0)
            other_revenue = activities_data.get('other_revenues', 0.0)
            net_assets_released = activities_data.get('net_assets_released', None)
            
            # Program service revenue = membership + meetings + education + project management (rounded)
            program_service_revenue = round(membership_dues + meetings_conferences + education_certification + project_management_fees)
            
            # Expense breakdown from functional expenses
            salaries_compensation = 0.0
            if functional_expenses:
                # Find salaries and wages from functional expenses
                for category in functional_expenses.categories:
                    if 'salaries' in category.category_name.lower() and 'wages' in category.category_name.lower():
                        salaries_compensation = category.total
                        break
            
            # If not found, try to get from activities
            if salaries_compensation == 0.0:
                # Calculate from functional expenses total employee compensation
                if functional_expenses:
                    for category in functional_expenses.categories:
                        if 'employee compensation' in category.category_name.lower():
                            salaries_compensation = category.total
                            break
            
            # Validate totals
            if functional_expenses:
                self._validate_functional_expenses(functional_expenses, total_expenses)
            
            # Create year data
            year_data = AuditedFinancialYearData(
                year=year,
                total_revenue=total_revenue,
                total_expenses=total_expenses,
                net_income=net_income,
                program_service_revenue=program_service_revenue,
                contributions_grants=contributions_grants,
                investment_income=investment_income,
                other_revenue=other_revenue,
                net_assets_released_from_restrictions=net_assets_released if net_assets_released is not None else None,
                membership_dues=membership_dues,
                membership_dues_organizational=membership_dues_org if membership_dues_org > 0 else None,
                membership_dues_individuals=membership_dues_ind if membership_dues_ind > 0 else None,
                meetings_conferences=meetings_conferences,
                education_certification=education_certification,
                project_management_fees=project_management_fees,
                salaries_compensation=salaries_compensation,
                other_expenses=(total_expenses - salaries_compensation) if total_expenses and salaries_compensation else 0.0,
                total_assets=balance_sheet_data.get('total_assets', 0.0),
                total_liabilities=balance_sheet_data.get('total_liabilities', 0.0),
                net_assets=balance_sheet_data.get('net_assets', 0.0),
                total_employees=0,  # May not be in audited statements
                total_volunteers=0,  # May not be in audited statements
                functional_expenses=functional_expenses
            )
            
            # Validate revenue totals
            self._validate_revenue_totals(year_data)
            
            return year_data
            
        except Exception as e:
            logger.error(f"Error extracting financial data for year {year}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_statement_of_financial_position(self, text: str, year: int) -> Dict[str, float]:
        """Parse Statement of Financial Position (Balance Sheet)"""
        data = {}
        
        # Find the Statement of Financial Position section - look for actual statement with "December 31"
        match = re.search(r'STATEMENTS?\s+OF\s+FINANCIAL\s+POSITION\s+December\s+31.*?(?=STATEMENTS?\s+OF|See independent|$)', text, re.IGNORECASE | re.DOTALL)
        if not match:
            return data
        
        section = match.group(0)
        
        # Extract year column - look for the year in the header
        # The format is usually "December 31, 2024" and "December 31, 2023"
        year_str = str(year)
        
        # Find TOTAL ASSETS (format: "TOTAL ASSETS $ 16,845,521 $ 17,538,558" or without dollar signs)
        assets_match = re.search(r'TOTAL\s+ASSETS\s+(?:\$\s*)?([\d,]+)\s+(?:\$\s*)?([\d,]+)', section, re.IGNORECASE)
        if assets_match:
            # Determine which value corresponds to our year
            # Usually the format is: 2024 value, then 2023 value
            if year == 2024:
                data['total_assets'] = self._parse_amount(assets_match.group(1))
            elif year == 2023:
                data['total_assets'] = self._parse_amount(assets_match.group(2))
        
        # Find TOTAL LIABILITIES (format: "TOTAL LIABILITIES $ 8,500,460 $ 8,208,678" or without dollar signs)
        liabilities_match = re.search(r'TOTAL\s+LIABILITIES\s+(?:\$\s*)?([\d,]+)\s+(?:\$\s*)?([\d,]+)', section, re.IGNORECASE)
        if liabilities_match:
            if year == 2024:
                data['total_liabilities'] = self._parse_amount(liabilities_match.group(1))
            elif year == 2023:
                data['total_liabilities'] = self._parse_amount(liabilities_match.group(2))
        
        # Find TOTAL NET ASSETS (format: "TOTAL NET ASSETS 8,345,061 9,329,880" or with dollar signs)
        net_assets_match = re.search(r'TOTAL\s+NET\s+ASSETS\s+(?:\$\s*)?([\d,]+)\s+(?:\$\s*)?([\d,]+)', section, re.IGNORECASE)
        if net_assets_match:
            if year == 2024:
                data['net_assets'] = self._parse_amount(net_assets_match.group(1))
            elif year == 2023:
                data['net_assets'] = self._parse_amount(net_assets_match.group(2))
        
        return data
    
    def _parse_statement_of_activities(self, text: str, year: int) -> Dict[str, float]:
        """Parse Statement of Activities (Income Statement)"""
        data = {}
        
        # Find the Statement of Activities section - look for the actual statement, not table of contents
        # The actual statement has "For the years ended December 31" or "For the year ended December 31" after the header
        match = re.search(r'STATEMENTS?\s+OF\s+ACTIVITIES\s+For\s+the\s+(?:years?|year)\s+ended.*?(?=STATEMENTS?\s+OF|See independent|$)', text, re.IGNORECASE | re.DOTALL)
        if not match:
            return data
        
        section = match.group(0)
        
        # Detect if this is a single-year or multi-year statement
        is_multi_year = bool(re.search(r'For the years ended', section, re.IGNORECASE))
        
        # Extract revenue items - look for patterns like "Membership dues" followed by amounts
        # The format is usually: "Organizational $ 2,809,755 $ 2,819,114"
        
        # Membership dues - Organizational (format: "Organizational $ 2,809,755 $ 2,819,114" or "Organizational 2,809,755 2,819,114")
        # For single-year statements, there's only one number
        org_match = re.search(r'Organizational\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if org_match:
            if is_multi_year and org_match.group(2):
                data['membership_dues_org'] = self._parse_amount(org_match.group(1) if year == 2024 else org_match.group(2))
            elif not is_multi_year:
                data['membership_dues_org'] = self._parse_amount(org_match.group(1))
        
        # Membership dues - Individuals and international affiliates
        ind_match = re.search(r'Individuals\s+and\s+international\s+affiliates\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if ind_match:
            if is_multi_year and ind_match.group(2):
                data['membership_dues_ind'] = self._parse_amount(ind_match.group(1) if year == 2024 else ind_match.group(2))
            elif not is_multi_year:
                data['membership_dues_ind'] = self._parse_amount(ind_match.group(1))
        
        # Meetings (format: "Meetings 1,996,248 1,689,359" or "Meetings 1,996,248" for single-year)
        meetings_match = re.search(r'^Meetings\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE | re.MULTILINE)
        if meetings_match:
            if is_multi_year and meetings_match.group(2):
                data['meetings'] = self._parse_amount(meetings_match.group(1) if year == 2024 else meetings_match.group(2))
            elif not is_multi_year:
                data['meetings'] = self._parse_amount(meetings_match.group(1))
        
        # Education and certification
        educ_match = re.search(r'Education\s+and\s+certification\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if educ_match:
            if is_multi_year and educ_match.group(2):
                data['education_certification'] = self._parse_amount(educ_match.group(1) if year == 2024 else educ_match.group(2))
            elif not is_multi_year:
                data['education_certification'] = self._parse_amount(educ_match.group(1))
        
        # Federal grant and contract revenue
        fed_match = re.search(r'Federal\s+grant\s+and\s+contract\s+revenue\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if fed_match:
            if is_multi_year and fed_match.group(2):
                data['federal_grants_contracts'] = self._parse_amount(fed_match.group(1) if year == 2024 else fed_match.group(2))
            elif not is_multi_year:
                data['federal_grants_contracts'] = self._parse_amount(fed_match.group(1))
        
        # Project management fees
        pm_match = re.search(r'Project\s+management\s+fees\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if pm_match:
            if is_multi_year and pm_match.group(2):
                data['project_management_fees'] = self._parse_amount(pm_match.group(1) if year == 2024 else pm_match.group(2))
            elif not is_multi_year:
                data['project_management_fees'] = self._parse_amount(pm_match.group(1))
        
        # Net investment return (loss) - note: may have negative values in parentheses
        inv_match = re.search(r'Net\s+investment\s+return\s+\(loss\)\s+(?:\(?([\d,]+)\)?|([\d,]+))(?:\s+(?:\(?([\d,]+)\)?|([\d,]+)))?', section, re.IGNORECASE)
        if inv_match:
            # Handle both positive and negative (in parentheses)
            val1 = inv_match.group(1) or inv_match.group(2) or '0'
            val2 = (inv_match.group(3) or inv_match.group(4)) if is_multi_year else None
            if is_multi_year and val2:
                data['investment_return'] = self._parse_amount(val1 if year == 2024 else val2)
            elif not is_multi_year:
                data['investment_return'] = self._parse_amount(val1)
        
        # Other revenues, gains and support
        other_match = re.search(r'Other\s+revenues?,\s+gains?\s+and\s+support\s+(?:\$\s*)?([\d,]+)(?:\s+(?:\$\s*)?([\d,]+))?', section, re.IGNORECASE)
        if other_match:
            if is_multi_year and other_match.group(2):
                data['other_revenues'] = self._parse_amount(other_match.group(1) if year == 2024 else other_match.group(2))
            elif not is_multi_year:
                data['other_revenues'] = self._parse_amount(other_match.group(1))
        
        # Net assets released from restrictions (may be negative, shown in parentheses)
        # Format: "Net assets released from restrictions $ 0 $ (25,519)" or "Net assets released from restrictions 0"
        # Note: _parse_amount handles parentheses conversion to negative automatically
        assets_released_match = re.search(r'Net\s+assets\s+released\s+from\s+restrictions\s+(?:\(\s*)?(?:\$\s*)?([\d,]+)(?:\s*\))?(?:\s+(?:\(\s*)?(?:\$\s*)?([\d,]+)(?:\s*\))?)?', section, re.IGNORECASE)
        if assets_released_match:
            if is_multi_year and assets_released_match.group(2):
                # For multi-year, extract the value for the target year
                val_str = assets_released_match.group(1) if year == 2024 else assets_released_match.group(2)
                # Extract the full line to check if value is in parentheses
                line_match = re.search(r'Net\s+assets\s+released\s+from\s+restrictions\s+.*', section, re.IGNORECASE)
                if line_match:
                    line = line_match.group(0)
                    # Find the position of our value in the line
                    val_pos = line.find(val_str)
                    if val_pos > 0:
                        # Check if there's an opening parenthesis before this value (and no closing before it)
                        before_val = line[:val_pos]
                        paren_pos = before_val.rfind('(')
                        if paren_pos >= 0 and ')' not in before_val[paren_pos:]:
                            data['net_assets_released'] = -self._parse_amount(val_str)
                        else:
                            data['net_assets_released'] = self._parse_amount(val_str)
                    else:
                        data['net_assets_released'] = self._parse_amount(val_str)
            elif not is_multi_year:
                val_str = assets_released_match.group(1)
                line_match = re.search(r'Net\s+assets\s+released\s+from\s+restrictions\s+.*', section, re.IGNORECASE)
                if line_match:
                    line = line_match.group(0)
                    val_pos = line.find(val_str)
                    if val_pos > 0:
                        before_val = line[:val_pos]
                        paren_pos = before_val.rfind('(')
                        if paren_pos >= 0 and ')' not in before_val[paren_pos:]:
                            data['net_assets_released'] = -self._parse_amount(val_str)
                        else:
                            data['net_assets_released'] = self._parse_amount(val_str)
                    else:
                        data['net_assets_released'] = self._parse_amount(val_str)
        
        # TOTAL REVENUES, GAINS, AND OTHER SUPPORT
        total_rev_match = re.search(r'TOTAL\s+REVENUES?,\s+GAINS?,\s+AND\s+OTHER\s+SUPPORT\s+([\d,]+)(?:\s+([\d,]+))?', section, re.IGNORECASE)
        if total_rev_match:
            if is_multi_year and total_rev_match.group(2):
                data['total_revenues'] = self._parse_amount(total_rev_match.group(1) if year == 2024 else total_rev_match.group(2))
            elif not is_multi_year:
                data['total_revenues'] = self._parse_amount(total_rev_match.group(1))
        
        # Expenses - Program services
        prog_match = re.search(r'Program\s+services\s+([\d,]+)(?:\s+([\d,]+))?', section, re.IGNORECASE)
        if prog_match:
            if is_multi_year and prog_match.group(2):
                data['program_services'] = self._parse_amount(prog_match.group(1) if year == 2024 else prog_match.group(2))
            elif not is_multi_year:
                data['program_services'] = self._parse_amount(prog_match.group(1))
        
        # Supporting services
        supp_match = re.search(r'Supporting\s+services\s+([\d,]+)(?:\s+([\d,]+))?', section, re.IGNORECASE)
        if supp_match:
            if is_multi_year and supp_match.group(2):
                data['supporting_services'] = self._parse_amount(supp_match.group(1) if year == 2024 else supp_match.group(2))
            elif not is_multi_year:
                data['supporting_services'] = self._parse_amount(supp_match.group(1))
        
        # TOTAL EXPENSES (format: "TOTAL EXPENSES 11,841,033 12,126,994" or "TOTAL EXPENSES 7,820,815" for single-year)
        total_exp_match = re.search(r'TOTAL\s+EXPENSES\s+([\d,]+)(?:\s+([\d,]+))?', section, re.IGNORECASE)
        if total_exp_match:
            if is_multi_year and total_exp_match.group(2):
                data['total_expenses'] = self._parse_amount(total_exp_match.group(1) if year == 2024 else total_exp_match.group(2))
            elif not is_multi_year:
                data['total_expenses'] = self._parse_amount(total_exp_match.group(1))
        
        return data
    
    def _parse_statement_of_functional_expenses(self, text: str, year: int) -> Optional[FunctionalExpensesData]:
        """Parse Statement of Functional Expenses"""
        # Find the Statement of Functional Expenses section
        # Look for the actual statement (not table of contents)
        # The table of contents has dots after "EXPENSES", the actual statement has "For the year ended" on the next line
        year_pattern = rf'For the year ended December 31, {year}'
        
        # Find all potential matches
        all_matches = list(re.finditer(r'STATEMENTS?\s+OF\s+FUNCTIONAL\s+EXPENSES', text, re.IGNORECASE))
        
        # Filter to find the actual statement (not table of contents)
        # The actual statement has "For the year ended" or year pattern within the next few lines
        match = None
        for m in all_matches:
            start = m.start()
            # Check the next 200 characters to see if this is the actual statement
            next_text = text[start:start+200]
            # Table of contents has dots or page numbers, actual statement has "For the year ended"
            if re.search(rf'For the year ended|with comparable.*{year}|{year_pattern}', next_text, re.IGNORECASE):
                # This is the actual statement - extract the full section
                # Find the end of this section (next statement or end of text)
                end_pattern = r'STATEMENTS?\s+OF\s+(?:FUNCTIONAL|CASH|See independent)'
                end_match = re.search(end_pattern, text[start+100:], re.IGNORECASE)
                if end_match:
                    section = text[start:start+100+end_match.start()]
                else:
                    section = text[start:]
                
                # Verify it contains the year pattern
                if re.search(year_pattern, section, re.IGNORECASE):
                    match = m
                    # Re-extract the full section for processing
                    end_match = re.search(end_pattern, text[start+100:], re.IGNORECASE)
                    if end_match:
                        section = text[start:start+100+end_match.start()]
                    else:
                        section = text[start:]
                    break
        
        if not match:
            return None
        
        # Section was already extracted above in the loop
        # If we somehow got here without section being set, extract it from match
        if 'section' not in locals():
            # Fallback: extract section from match
            start = match.start()
            end_pattern = r'STATEMENTS?\s+OF\s+(?:FUNCTIONAL|CASH|See independent)'
            end_match = re.search(end_pattern, text[start+100:], re.IGNORECASE)
            if end_match:
                section = text[start:start+100+end_match.start()]
            else:
                section = text[start:]
        
        # Detect if this is a single-year or multi-year statement
        # Check the header: 
        # - "For the year ended December 31, 2023 with comparable totals for 2022" = single-year format (2023 is primary)
        # - "For the years ended December 31, 2024 and 2023" = multi-year format (side-by-side)
        # - "For the year ended December 31, 2024 with comparable totals for 2023" = multi-year format (2024 is primary, 2023 is comparison)
        header_match = re.search(r'For the (?:years?|year) ended December 31, (\d{4})', section, re.IGNORECASE)
        if header_match:
            header_year = int(header_match.group(1))
            # Check if it says "years" (plural) = multi-year format
            if re.search(r'For the years ended', section, re.IGNORECASE):
                is_multi_year = True
            elif header_year == year:
                # Header year matches target year - this is single-year format for our target year
                # Even if it has "with comparable totals for", the structure is still single-year
                is_multi_year = False
            else:
                # Header year doesn't match target year - check structure
                # If it says "with comparable totals for" and header year is different, it's multi-year format
                if re.search(rf'with comparable totals for.*{year}', section, re.IGNORECASE):
                    is_multi_year = True
                else:
                    is_multi_year = False
        else:
            # Fallback: check for two year columns at the end
            is_multi_year = bool(re.search(r'\d{4}\s+\d{4}', section))
        
        # Parse the table - it has columns for Program Services (with subcategories) and Supporting Services
        # The format is typically:
        # Category Name | Program Services columns | Supporting Services columns | Total columns
        
        categories = []
        total_program_services = 0.0
        total_supporting_services = 0.0
        
        # Look for expense categories - they're typically listed with dollar amounts
        # Common categories: Employee Compensation, Salaries and wages, Pension plan contribution, etc.
        
        # Find all lines that look like expense categories with amounts
        # Pattern: Category name, then dollar amounts in columns
        lines = section.split('\n')
        
        current_category = None
        category_program = 0.0
        category_supporting = 0.0
        
        # Look for the "Total expenses" row to get overall totals
        # For multi-year: "Total expenses $ X,XXX,XXX $ Y,YYY,YYY $ Z,ZZZ,ZZZ $ A,AAA,AAA"
        #   Where: Program Total (2024) | Supporting Total (2024) | Program Total (2023) | Supporting Total (2023)
        #   Or: Program Total | Supporting Total | Year Total (2024) | Year Total (2023)
        # For single-year: "Total expenses $ X,XXX,XXX $ Y,YYY,YYY $ Z,ZZZ,ZZZ"
        #   Where: Program Total | Supporting Total | Year Total
        total_match = re.search(r'Total\s+expenses?\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)(?:\s+\$\s*([\d,]+))?', section, re.IGNORECASE)
        if total_match:
            if is_multi_year and total_match.group(4):
                # Multi-year with 4 totals: Program (2024) | Supporting (2024) | Program (2023) | Supporting (2023)
                # Or: Program Total | Supporting Total | Year Total (2024) | Year Total (2023)
                if year == 2024:
                    total_program_services = self._parse_amount(total_match.group(1))
                    total_supporting_services = self._parse_amount(total_match.group(2))
                else:  # 2023
                    total_program_services = self._parse_amount(total_match.group(3))
                    total_supporting_services = self._parse_amount(total_match.group(4))
            elif is_multi_year:
                # Multi-year with 3 totals: might be Program | Supporting | Year Total (2024) | Year Total (2023) but only 3 captured
                # Actually, let's look for the pattern more carefully
                # The structure from the PDF shows: Program subcats | Program Total | Supporting subcats | Supporting Total | Year Total (2024) | Year Total (2023)
                # So for "Total expenses" row, it should have: Program Total | Supporting Total | Year Total (2024) | Year Total (2023)
                if year == 2024:
                    total_program_services = self._parse_amount(total_match.group(1))
                    total_supporting_services = self._parse_amount(total_match.group(2))
                else:  # 2023
                    # For 2023, we'd need the last number, but we only have 3 groups
                    # This means the pattern might be different - let's calculate from categories
                    pass
            else:
                # Single-year: Program Total | Supporting Total | Year Total
                total_program_services = self._parse_amount(total_match.group(1))
                total_supporting_services = self._parse_amount(total_match.group(2))
        
        # Parse individual expense categories
        # Look for patterns like "Salaries and wages $ 791,601 $ - $ 389,996 ..."
        category_patterns = [
            (r'Salaries\s+and\s+wages\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Salaries and wages'),
            (r'Pension\s+plan\s+contribution\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Pension plan contribution'),
            (r'Other\s+employee\s+benefits\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Other employee benefits'),
            (r'Payroll\s+taxes\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Payroll taxes'),
            (r'Management\s+fees\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Management fees'),
            (r'Legal\s+fees\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Legal fees'),
            (r'Accounting\s+fees\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)\s+\$\s*([\d,]+)', 'Accounting fees'),
        ]
        
        # More flexible pattern - find category name followed by dollar amounts
        # The structure seems to be: Category | Program subcategories | Supporting subcategories | Totals
        # We need to find the right column for the year
        
        # For single-year statements, find the Employee Compensation total line to understand column structure
        employee_comp_total_line = None
        if not is_multi_year:
            for line in lines:
                # Look for the Employee Compensation total line (usually has "181,367" or similar pattern)
                if 'Employee Compensation' not in line and len(re.findall(r'\$\s*[\d,]+', re.sub(r'(\d)\s+(\d)', r'\1\2', line))) >= 3:
                    # Check if this looks like a total line (has multiple similar-sized numbers that sum)
                    amounts = re.findall(r'\$\s*([\d,]+)', re.sub(r'(\d)\s+(\d)', r'\1\2', line))
                    if len(amounts) >= 3:
                        # Check if the last three numbers make sense (Program + Supporting = Total)
                        try:
                            prog = self._parse_amount(amounts[-3])
                            supp = self._parse_amount(amounts[-2])
                            tot = self._parse_amount(amounts[-1])
                            if abs((prog + supp) - tot) < 1000:  # They sum correctly
                                employee_comp_total_line = line
                                break
                        except:
                            pass
        
        # Parse individual expense categories
        # For multi-year: Structure is: Category | Program subcats | Program Total | Supporting subcats | Supporting Total | Year Total (2024) | Year Total (2023)
        # For single-year: Structure is: Category | Program subcats | Program Total | Supporting subcats | Supporting Total | Year Total
        
        # Track categories we've already added to prevent duplicates
        seen_categories = set()
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header lines and non-expense lines
            line_upper = line.upper()
            # Skip column headers (but allow expense category names)
            if line_upper in ['PROGRAM SERVICES', 'SUPPORTING SERVICES', 'TOTAL', 'TOTALS']:
                continue
            # Skip lines that are clearly headers (contain "PROGRAM SERVICES" or "SUPPORTING SERVICES" as standalone headers)
            if line_upper.strip() in ['PROGRAM SERVICES', 'SUPPORTING SERVICES']:
                continue
            # Skip subcategory headers like "Membership, Meetings and Education" when they appear as standalone headers
            if line_upper in ['MEMBERSHIP, MEETINGS AND EDUCATION', 'STANDARDS DEVELOPMENT, PMO AND TOOLING', 
                            'FEDERAL GRANT PROJECTS', 'MANAGEMENT AND GENERAL', 'MEMBERSHIP DEVELOPMENT']:
                continue
            
            # Skip balance sheet items and other non-expense categories
            if any(item in line_upper for item in ['CASH AND', 'ACCOUNTS RECEIVABLE', 'INVESTMENTS', 'TOTAL ASSETS', 
                                                     'TOTAL LIABILITIES', 'NET ASSETS', 'ORGANIZATIONAL', 'INDIVIDUALS AND',
                                                     'NET ASSETS AT', 'CHANGE IN NET', 'BEGINNING OF YEAR', 'END OF YEAR',
                                                     'REVENUE', 'INCOME', 'STATEMENT OF']):
                continue
            
            # Look for lines that have a category name followed by dollar amounts
            # Pattern: Category name, then multiple dollar amounts
            # Note: PDF extraction may add spaces within numbers (e.g., "1 68,525" should be "168,525")
            # First, clean up spaces within numbers
            line_cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', line)  # Remove spaces between digits
            
            # Extract all dollar amounts - be more flexible with patterns
            # Try multiple patterns: with $, without $, with parentheses for negatives
            dollar_amounts = []
            
            # Pattern 1: $ 123,456 or $123,456
            amounts_with_dollar = re.findall(r'\$\s*([\d,]+)', line_cleaned)
            dollar_amounts.extend(amounts_with_dollar)
            
            # Pattern 2: Numbers with commas (at least 4 digits total: 1,000 or more)
            # Also match numbers without commas if they're 4+ digits
            number_patterns = re.findall(r'\b([\d]{1,3}(?:,\d{3})+)\b', line_cleaned)
            # Also find standalone 4+ digit numbers
            large_numbers = re.findall(r'\b(\d{4,})\b', line_cleaned)
            
            # Filter out numbers that are too small (likely not dollar amounts)
            for num in number_patterns:
                num_clean = num.replace(',', '')
                if len(num_clean) >= 4:  # At least 4 digits (1000+)
                    if num not in dollar_amounts:
                        dollar_amounts.append(num)
            
            # Add large numbers without commas
            for num in large_numbers:
                if num not in dollar_amounts:
                    # Check if it's not part of a comma-formatted number we already found
                    is_duplicate = False
                    for existing in dollar_amounts:
                        if num in existing.replace(',', ''):
                            is_duplicate = True
                            break
                    if not is_duplicate and len(num) >= 4:
                        dollar_amounts.append(num)
            
            # Pattern 3: Numbers in parentheses (negative amounts)
            negative_amounts = re.findall(r'\(([\d,]+)\)', line_cleaned)
            dollar_amounts.extend(negative_amounts)
            
            # Remove duplicates while preserving order
            seen = set()
            dollar_amounts_unique = []
            for amt in dollar_amounts:
                if amt not in seen:
                    seen.add(amt)
                    dollar_amounts_unique.append(amt)
            dollar_amounts = dollar_amounts_unique
            
            # Need at least 2 amounts to be a valid expense category row
            if len(dollar_amounts) >= 2:
                # Extract category name (everything before the first dollar amount)
                # Try multiple patterns to find the category name
                category_name = None
                
                # Pattern 1: Everything before first $ sign
                category_match = re.match(r'^([^$]+?)\s+\$', line)
                if category_match:
                    category_name = category_match.group(1).strip()
                
                # Pattern 2: Find first number (with or without comma) and take everything before it
                if not category_name:
                    # Find the position of the first number pattern
                    first_number_match = re.search(r'[\d]{1,3}(?:,\d{3})+|\d{4,}|[\d]{2,}', line_cleaned)
                    if first_number_match:
                        first_number_pos = first_number_match.start()
                        potential_name = line_cleaned[:first_number_pos].strip()
                        # Clean it up - remove trailing dashes, spaces, etc.
                        potential_name = re.sub(r'[\s\-]+$', '', potential_name)
                        # Make sure it looks like a category name (starts with letter, has reasonable length)
                        if len(potential_name) >= 3 and re.match(r'^[A-Za-z]', potential_name):
                            if potential_name.lower() not in ['total', 'subtotal', 'program', 'supporting', 'expenses']:
                                category_name = potential_name
                
                # Pattern 3: Split on first occurrence of a dollar sign or number pattern (fallback)
                if not category_name:
                    # Find the position of the first dollar amount or large number
                    first_amount_pos = len(line_cleaned)
                    for pattern in [r'\$\s*[\d,]', r'\b[\d]{1,3}(?:,\d{3})+', r'\b\d{4,}']:
                        match = re.search(pattern, line_cleaned)
                        if match and match.start() < first_amount_pos:
                            first_amount_pos = match.start()
                    if first_amount_pos < len(line_cleaned) and first_amount_pos > 0:
                        potential_name = line_cleaned[:first_amount_pos].strip()
                        potential_name = re.sub(r'[\s\-]+$', '', potential_name)
                        if len(potential_name) >= 3 and re.match(r'^[A-Za-z]', potential_name):
                            category_name = potential_name
                
                if category_name:
                    # Clean up category name
                    category_name = re.sub(r'\s+', ' ', category_name)  # Normalize whitespace
                    category_name = category_name.strip('.,;:')  # Remove trailing punctuation
                    # Remove common prefixes/suffixes that might be artifacts
                    category_name = re.sub(r'^(Subtotal|Total|Program|Supporting)\s+', '', category_name, flags=re.IGNORECASE)
                    # Remove trailing numbers that indicate duplicates (e.g., "Category 1" -> "Category")
                    category_name = re.sub(r'\s+\d+$', '', category_name)
                    category_name = category_name.strip()
                else:
                    # If we can't extract a category name, skip this line
                    continue
                
                # Skip if this looks like a header, subtotal, or section header
                category_lower = category_name.lower()
                
                # Skip section headers and subtotals (but keep "Total expenses" at the end)
                skip_patterns = [
                    r'^subtotal', r'^total$', r'^program services$', r'^supporting services$',
                    r'^employee compensation$', r'^other expenses$',
                    r'^membership,?\s+meetings', r'^standards development', r'^federal grant',
                    r'^management and general$', r'^membership development$'
                ]
                
                is_skip = False
                for pattern in skip_patterns:
                    if re.match(pattern, category_lower):
                        # But allow "Total expenses" at the end
                        if 'total expenses' in category_lower or (category_lower == 'total' and i > len(lines) - 5):
                            # This is the final totals row - handle separately
                            if 'total expenses' in category_lower or category_lower.strip() == 'total':
                                # Extract totals from this row
                                if is_multi_year:
                                    # For multi-year: last two numbers are 2024 and 2023 totals
                                    if len(dollar_amounts) >= 2:
                                        if year == 2024:
                                            total_program_services = self._parse_amount(dollar_amounts[-2]) if len(dollar_amounts) >= 4 else 0.0
                                            total_supporting_services = self._parse_amount(dollar_amounts[-3]) if len(dollar_amounts) >= 4 else 0.0
                                        else:  # 2023
                                            total_program_services = self._parse_amount(dollar_amounts[-1]) if len(dollar_amounts) >= 4 else 0.0
                                            total_supporting_services = self._parse_amount(dollar_amounts[-2]) if len(dollar_amounts) >= 4 else 0.0
                                else:
                                    # Single-year: last number is program total, second-to-last is supporting total
                                    if len(dollar_amounts) >= 2:
                                        total_program_services = self._parse_amount(dollar_amounts[-2])
                                        total_supporting_services = self._parse_amount(dollar_amounts[-1])
                        is_skip = True
                        break
                    
                    if is_skip:
                        continue
                    
                    # For regular categories, extract the total for the target year
                    if is_multi_year:
                        # Multi-year format has two structures:
                        # 1. "For the year ended December 31, 2024 with comparable totals for 2023"
                        #    Structure: Program subcats (2024) | Program Total (2024) | Supporting subcats (2024) | Supporting Total (2024) | Year Total (2024) | Year Total (2023)
                        #    For 2024: second-to-last, For 2023: last (but 2023 has no program/supporting breakdown)
                        # 2. "For the years ended December 31, 2023 and 2022" (side-by-side, both years have breakdowns)
                        #    Structure: Program subcats | Program Total (2023) | Program Total (2022) | Supporting subcats | Supporting Total (2023) | Supporting Total (2022) | Year Total (2023) | Year Total (2022)
                        
                        # Check header to determine structure
                        has_comparable_totals = 'with comparable totals for' in section.lower()
                        is_side_by_side = re.search(r'For the years ended', section, re.IGNORECASE) and not has_comparable_totals
                        
                        if has_comparable_totals:
                            # Structure 1: "with comparable totals" - only primary year has breakdown
                            # Year totals are the last two numbers
                            if len(dollar_amounts) >= 2:
                                # Find which year is primary (first mentioned in header)
                                header_year_match = re.search(r'For the year ended December 31, (\d{4})', section, re.IGNORECASE)
                                primary_year = int(header_year_match.group(1)) if header_year_match else None
                                
                                if year == primary_year:
                                    total = self._parse_amount(dollar_amounts[-2])  # Second-to-last (primary year)
                                else:
                                    total = self._parse_amount(dollar_amounts[-1])  # Last (comparison year, no breakdown)
                            else:
                                continue
                        elif is_side_by_side:
                            # Structure 2: Side-by-side - both years have breakdowns
                            # The structure is: ... | Program Total (year1) | Program Total (year2) | Supporting Total (year1) | Supporting Total (year2) | Year Total (year1) | Year Total (year2)
                            # For "For the years ended December 31, 2023 and 2022":
                            #   - 2023 is first mentioned, so its totals are at indices before 2022's
                            #   - Year totals are the last two: second-to-last is 2023, last is 2022
                            if len(dollar_amounts) >= 2:
                                # Find which year is mentioned first in header
                                header_years_match = re.search(r'For the years ended December 31, (\d{4})\s+and\s+(\d{4})', section, re.IGNORECASE)
                                if header_years_match:
                                    first_year = int(header_years_match.group(1))
                                    second_year = int(header_years_match.group(2))
                                    
                                    if year == first_year:
                                        total = self._parse_amount(dollar_amounts[-2])  # Second-to-last (first year)
                                    elif year == second_year:
                                        total = self._parse_amount(dollar_amounts[-1])  # Last (second year)
                                    else:
                                        continue
                                else:
                                    # Fallback: assume higher year is first
                                    if year == max([y for y in [2022, 2023, 2024] if str(y) in section]):
                                        total = self._parse_amount(dollar_amounts[-2])  # Second-to-last
                                    else:
                                        total = self._parse_amount(dollar_amounts[-1])  # Last
                            else:
                                continue
                        else:
                            # Fallback: use same logic as before
                            if len(dollar_amounts) >= 2:
                                if year == 2024:
                                    total = self._parse_amount(dollar_amounts[-2])  # Second-to-last
                                else:  # 2023
                                    total = self._parse_amount(dollar_amounts[-1])  # Last
                            else:
                                continue
                    else:
                        # Single-year format: ... | Program subcats | Program Total | Supporting subcats | Supporting Total | Year Total (current) | Year Total (previous)
                        # For "Salaries and wages" in 2022-2023 PDF: [168,525, 168,525, 467,204, 467,204, 635,729, 325,356]
                        # Structure: Program subcat1 | Program Total | Supporting subcat1 | Supporting Total | Year Total (2023) | Year Total (2022)
                        # The current year (2023) total is second-to-last, previous year (2022) is last
                        if len(dollar_amounts) >= 2:
                            # Use second-to-last as the current year total when there's a previous year shown
                            # This matches the pattern "For the year ended December 31, 2023 with comparable totals for 2022"
                            if len(dollar_amounts) >= 3:
                                # Has previous year - current year is second-to-last
                                total = self._parse_amount(dollar_amounts[-2])  # Second-to-last (current year)
                            else:
                                # Only one year shown
                                total = self._parse_amount(dollar_amounts[-1])  # Last (only year)
                        else:
                            continue
                    
                    # Extract program and supporting amounts
                    # The structure for multi-year is complex:
                    # Program subcat1 | (empty/-) | Program subcat2 | Program subtotal1 | Program subcat3 | Supporting subcat1 | Supporting subtotal | Year Total (2024) | Year Total (2023)
                    # For "Salaries and wages": 791,601 | - | 389,996 | 1,181,597 | 2,323,220 | 342,508 | 2,665,728 | 3,847,325 | 635,729
                    # So: Program = 1,181,597 + 2,323,220 = 3,504,817, Supporting = 2,665,728
                    # The structure shows program subtotals that need to be summed
                    program_amount = 0.0
                    supporting_amount = 0.0
                    
                    if is_multi_year:
                        # Check if this is side-by-side (both years have breakdowns) or "with comparable totals" (only primary has breakdown)
                        has_comparable_totals = 'with comparable totals for' in section.lower()
                        is_side_by_side = re.search(r'For the years ended', section, re.IGNORECASE) and not has_comparable_totals
                        
                        if is_side_by_side:
                            # Side-by-side format: both years have program/supporting breakdowns
                            # Structure: ... | Program Total (year1) | Program Total (year2) | Supporting Total (year1) | Supporting Total (year2) | Year Total (year1) | Year Total (year2)
                            # For "For the years ended December 31, 2023 and 2022":
                            #   Program Total (2023) is before Program Total (2022)
                            #   Supporting Total (2023) is before Supporting Total (2022)
                            #   Year Total (2023) is second-to-last, Year Total (2022) is last
                            
                            if len(dollar_amounts) >= 6:
                                # Find which year is first in header
                                header_years_match = re.search(r'For the years ended December 31, (\d{4})\s+and\s+(\d{4})', section, re.IGNORECASE)
                                if header_years_match:
                                    first_year = int(header_years_match.group(1))
                                    second_year = int(header_years_match.group(2))
                                    
                                    # The structure has: Program Total (first), Program Total (second), Supporting Total (first), Supporting Total (second), Year Total (first), Year Total (second)
                                    # So for first year: Program at index -5, Supporting at index -3, Year Total at index -2
                                    # For second year: Program at index -4, Supporting at index -2, Year Total at index -1
                                    if year == first_year:
                                        if len(dollar_amounts) >= 6:
                                            program_amount = self._parse_amount(dollar_amounts[-5])  # Program Total (first year)
                                            supporting_amount = self._parse_amount(dollar_amounts[-3])  # Supporting Total (first year)
                                            # Validate
                                            if abs((program_amount + supporting_amount) - total) > 1000:
                                                supporting_amount = self._parse_amount(dollar_amounts[-3])
                                                program_amount = max(0.0, total - supporting_amount)
                                    elif year == second_year:
                                        if len(dollar_amounts) >= 6:
                                            program_amount = self._parse_amount(dollar_amounts[-4])  # Program Total (second year)
                                            supporting_amount = self._parse_amount(dollar_amounts[-2])  # Supporting Total (second year)
                                            # Validate
                                            if abs((program_amount + supporting_amount) - total) > 1000:
                                                supporting_amount = self._parse_amount(dollar_amounts[-2])
                                                program_amount = max(0.0, total - supporting_amount)
                        elif has_comparable_totals:
                            # "With comparable totals" format: only primary year has breakdown
                            # Structure: Program subcats (primary) | Program Total (primary) | Supporting subcats (primary) | Supporting Total (primary) | Year Total (primary) | Year Total (comparison)
                            if len(dollar_amounts) >= 4:
                                # Find which year is primary
                                header_year_match = re.search(r'For the year ended December 31, (\d{4})', section, re.IGNORECASE)
                                primary_year = int(header_year_match.group(1)) if header_year_match else None
                                
                                if year == primary_year:
                                    # Primary year has breakdown
                                    program_amount = self._parse_amount(dollar_amounts[-4])  # Program Total (primary)
                                    supporting_amount = self._parse_amount(dollar_amounts[-3])  # Supporting Total (primary)
                                    # Validate
                                    if abs((program_amount + supporting_amount) - total) > 1000:
                                        supporting_amount = self._parse_amount(dollar_amounts[-3])
                                        program_amount = max(0.0, total - supporting_amount)
                                else:
                                    # Comparison year - no breakdown available
                                    program_amount = 0.0
                                    supporting_amount = 0.0
                            else:
                                program_amount = 0.0
                                supporting_amount = 0.0
                        else:
                            # Fallback: try to extract for 2024
                            if len(dollar_amounts) >= 4 and year == 2024:
                                program_amount = self._parse_amount(dollar_amounts[-4])
                                supporting_amount = self._parse_amount(dollar_amounts[-3])
                                if abs((program_amount + supporting_amount) - total) > 1000:
                                    supporting_amount = self._parse_amount(dollar_amounts[-3])
                                    program_amount = max(0.0, total - supporting_amount)
                            else:
                                program_amount = 0.0
                                supporting_amount = 0.0
                    else:
                        # Single-year format structure (with comparable totals for prior year):
                        # Program subcat1 | Program Total | Supporting subcat1 | Supporting Total | Year Total (current) | Year Total (previous)
                        # For "Salaries and wages" in 2022-2023 PDF: [168,525, 168,525, 467,204, 467,204, 635,729, 325,356]
                        # Structure: Program subcat (2023) | Program Total (2023) | Supporting subcat (2023) | Supporting Total (2023) | Total 2023 (penultimate) | Total 2022 (rightmost)
                        # Program Total is at index 1 (168,525), Supporting Total is at index 3 (467,204), Year Total (2023) is at index 4 (635,729)
                        
                        # The structure is consistent: Program Total at index 1, Supporting Total at index 3, Current Year Total at index -2
                        if len(dollar_amounts) >= 6:
                            # Standard structure with 6 amounts
                            program_amount = self._parse_amount(dollar_amounts[1])  # Program Total (index 1)
                            supporting_amount = self._parse_amount(dollar_amounts[3])  # Supporting Total (index 3)
                            # Validate they sum to the current year total (which should be at index -2)
                            current_year_total = self._parse_amount(dollar_amounts[-2])
                            if abs((program_amount + supporting_amount) - current_year_total) > 1000:
                                # Doesn't match - try to find by searching
                                found_match = False
                                for prog_idx in range(len(dollar_amounts) - 2):  # Don't check last 2 (year totals)
                                    for supp_idx in range(prog_idx + 1, len(dollar_amounts) - 1):  # Don't check last (previous year total)
                                        try:
                                            prog_candidate = self._parse_amount(dollar_amounts[prog_idx])
                                            supp_candidate = self._parse_amount(dollar_amounts[supp_idx])
                                            # Check if they sum to the total
                                            if abs((prog_candidate + supp_candidate) - total) < 1000:
                                                program_amount = prog_candidate
                                                supporting_amount = supp_candidate
                                                found_match = True
                                                break
                                        except:
                                            continue
                                    if found_match:
                                        break
                                if not found_match:
                                    # Fallback: calculate from total
                                    supporting_amount = self._parse_amount(dollar_amounts[-3]) if len(dollar_amounts) >= 3 else 0.0
                                    program_amount = max(0.0, total - supporting_amount)
                        elif len(dollar_amounts) >= 4:
                            # Simpler structure - try to find program and supporting
                            found_match = False
                            for prog_idx in range(len(dollar_amounts) - 1):  # Don't check last (year total)
                                for supp_idx in range(prog_idx + 1, len(dollar_amounts) - 1):
                                    try:
                                        prog_candidate = self._parse_amount(dollar_amounts[prog_idx])
                                        supp_candidate = self._parse_amount(dollar_amounts[supp_idx])
                                        if abs((prog_candidate + supp_candidate) - total) < 1000:
                                            program_amount = prog_candidate
                                            supporting_amount = supp_candidate
                                            found_match = True
                                            break
                                    except:
                                        continue
                                if found_match:
                                    break
                            if not found_match:
                                # Fallback
                                supporting_amount = self._parse_amount(dollar_amounts[-2]) if len(dollar_amounts) >= 2 else 0.0
                                program_amount = max(0.0, total - supporting_amount)
                        else:
                            program_amount = 0.0
                            supporting_amount = 0.0
                    
                    if total > 0:
                        # Normalize category name for deduplication (remove trailing numbers)
                        normalized_key = re.sub(r'\s+\d+$', '', category_name.lower().strip())
                        
                        # Check if we've already added this category (prevent duplicates)
                        if normalized_key not in seen_categories:
                            seen_categories.add(normalized_key)
                            # Use the normalized name (without trailing number) as the category name
                            clean_category_name = re.sub(r'\s+\d+$', '', category_name).strip()
                            categories.append(FunctionalExpenseCategory(
                                category_name=clean_category_name,
                                program_services=program_amount,
                                supporting_services=supporting_amount,
                                total=total
                            ))
                        else:
                            # Update existing category if this one has better data (non-zero program/supporting)
                            for existing_cat in categories:
                                existing_normalized = re.sub(r'\s+\d+$', '', existing_cat.category_name.lower().strip())
                                if existing_normalized == normalized_key:
                                    # If existing has zero program/supporting but this one doesn't, update it
                                    if (existing_cat.program_services == 0 and existing_cat.supporting_services == 0) and \
                                       (program_amount > 0 or supporting_amount > 0):
                                        existing_cat.program_services = program_amount
                                        existing_cat.supporting_services = supporting_amount
                                        # Also update total if this one is better
                                        if total > existing_cat.total * 0.9:  # Within 10% - likely the same category
                                            existing_cat.total = total
                                    # If both have data, prefer the one with higher total (more complete)
                                    elif (program_amount > 0 or supporting_amount > 0) and total > existing_cat.total:
                                        existing_cat.program_services = program_amount
                                        existing_cat.supporting_services = supporting_amount
                                        existing_cat.total = total
                                    break
        
        # If we didn't find totals, calculate them
        if total_program_services == 0.0:
            total_program_services = sum(cat.program_services for cat in categories)
        if total_supporting_services == 0.0:
            total_supporting_services = sum(cat.supporting_services for cat in categories)
        
        total_expenses = total_program_services + total_supporting_services
        
        return FunctionalExpensesData(
            year=year,
            categories=categories,
            total_program_services=total_program_services,
            total_supporting_services=total_supporting_services,
            total_expenses=total_expenses
        )
    
    def _extract_amount(self, text: str, pattern: str, year: int, tables: List) -> Optional[float]:
        """Extract a monetary amount from text or tables"""
        # Try text search first
        regex = re.compile(pattern, re.IGNORECASE)
        matches = regex.finditer(text)
        
        for match in matches:
            # Look for numbers near the match
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            context = text[context_start:context_end]
            
            # Look for dollar amounts
            amount_patterns = [
                r'\$[\d,]+(?:\.\d{2})?',
                r'[\d,]+(?:\.\d{2})?\s*(?:million|thousand|M|K)?',
            ]
            
            for amt_pattern in amount_patterns:
                amounts = re.findall(amt_pattern, context)
                if amounts:
                    # Take the first amount found
                    amount_str = amounts[0].replace('$', '').replace(',', '')
                    try:
                        amount = float(amount_str)
                        # Handle millions/thousands
                        if 'million' in context.lower() or 'M' in context:
                            amount *= 1000000
                        elif 'thousand' in context.lower() or 'K' in context:
                            amount *= 1000
                        return amount
                    except ValueError:
                        continue
        
        # Try table search
        for table in tables:
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                if regex.search(row_text):
                    # Look for numbers in the same row
                    for cell in row:
                        if cell:
                            cell_str = str(cell).replace('$', '').replace(',', '').strip()
                            try:
                                amount = float(cell_str)
                                return amount
                            except ValueError:
                                continue
        
        return None
    
    def _parse_functional_expenses_table(self, text: str, year: int, tables: List) -> Optional[FunctionalExpensesData]:
        """Parse the Statement of Functional Expenses table using pdfplumber table extraction"""
        functional_table = None
        
        # Find the table that contains functional expenses data
        # Look for tables with "Program Services" and "Supporting Services" headers
        for table in tables:
            if not table or len(table) < 3:
                continue
            
            # Check if this table has functional expenses structure
            table_text = ' '.join([' '.join([str(cell) if cell else '' for cell in row]) for row in table if row])
            table_text_lower = table_text.lower()
            
            # Must have both program and supporting services references
            has_program = 'program services' in table_text_lower or 'program' in table_text_lower
            has_supporting = 'supporting services' in table_text_lower or 'supporting' in table_text_lower
            has_expense_categories = any(cat in table_text_lower for cat in ['salaries', 'wages', 'pension', 'legal fees', 'accounting', 'travel', 'conferences'])
            
            if has_program and has_supporting and has_expense_categories:
                # Also check if it has the year we're looking for
                if str(year) in table_text or f'for the year ended december 31, {year}' in table_text_lower:
                    functional_table = table
                    break
        
        if not functional_table:
            return None
        
        # Parse the table
        categories = []
        total_program_services = 0.0
        total_supporting_services = 0.0
        
        # Find header row and column structure
        # The table structure for 2024 is complex with subcategories:
        # Category | Membership/Meetings/Education | Standards Dev/PMO | Federal Grants | Program Total | Management/General | Membership Dev | Supporting Total | Total 2024 | Total 2023
        
        header_row_idx = None
        category_col_idx = 0  # First column is usually category name
        
        # Find columns for Program Services Total and Supporting Services Total
        # Also need to find the year total columns
        program_total_col_idx = None
        supporting_total_col_idx = None
        year_total_col_idx = None  # For the target year
        year_prior_col_idx = None  # For prior year (if multi-year)
        
        # Look for header row - it should have "Program Services", "Supporting Services", and year references
        for i, row in enumerate(functional_table[:10]):  # Check first 10 rows for header
            if not row:
                continue
            row_text = ' '.join([str(cell) if cell else '' for cell in row]).lower()
            
            # Check if this looks like a header row
            if 'program services' in row_text or ('program' in row_text and 'total' in row_text):
                header_row_idx = i
                
                # Find column indices by looking for key terms
                for j, cell in enumerate(row):
                    if not cell:
                        continue
                    cell_str = str(cell).lower().strip()
                    
                    # Look for "Total" columns that indicate Program/Supporting totals
                    if 'total' in cell_str:
                        # Check context - is this Program Total or Supporting Total?
                        # Look at surrounding cells
                        if j > 0 and j < len(row) - 1:
                            prev_cell = str(row[j-1]).lower() if j > 0 and row[j-1] else ''
                            next_cell = str(row[j+1]).lower() if j < len(row)-1 and row[j+1] else ''
                            
                            if 'program' in prev_cell or 'program' in cell_str:
                                program_total_col_idx = j
                            elif 'supporting' in prev_cell or 'supporting' in cell_str or 'management' in prev_cell:
                                supporting_total_col_idx = j
                            elif str(year) in cell_str or (j > category_col_idx + 3 and not program_total_col_idx):
                                # This might be a year total column
                                if not year_total_col_idx:
                                    year_total_col_idx = j
                                else:
                                    year_prior_col_idx = j
                
                # Also look for year columns in header
                for j, cell in enumerate(row):
                    if cell and str(year) in str(cell):
                        year_total_col_idx = j
                    elif cell and j > year_total_col_idx if year_total_col_idx else False:
                        # Check if this is prior year
                        cell_str = str(cell)
                        if any(str(y) in cell_str for y in range(2019, year)):
                            year_prior_col_idx = j
                
                break
        
        if header_row_idx is None:
            # Try to infer header - look for row with "Total" and year numbers
            for i, row in enumerate(functional_table[:5]):
                if not row:
                    continue
                row_text = ' '.join([str(cell) if cell else '' for cell in row]).lower()
                if 'total' in row_text and (str(year) in ' '.join([str(c) for c in row if c]) or '2024' in ' '.join([str(c) for c in row if c])):
                    header_row_idx = i
                    # Try to find total columns by position
                    # Usually: category (0), program subcats, program total, supporting subcats, supporting total, year totals
                    if len(row) >= 6:
                        # Heuristic: program total is usually around index 4-5, supporting around 6-7, year totals at end
                        for j in range(len(row)):
                            cell_str = str(row[j]).lower() if row[j] else ''
                            if 'total' in cell_str:
                                if not program_total_col_idx and j < len(row) / 2:
                                    program_total_col_idx = j
                                elif not supporting_total_col_idx and j > (program_total_col_idx if program_total_col_idx else 0):
                                    supporting_total_col_idx = j
                    break
        
        if header_row_idx is None:
            return None
        
        # Parse data rows
        for i in range(header_row_idx + 1, len(functional_table)):
            row = functional_table[i]
            if not row or len(row) < 2:
                continue
            
            # Get category name (first column)
            category_name = str(row[category_col_idx]).strip() if category_col_idx < len(row) and row[category_col_idx] else ""
            if not category_name:
                continue
            
            category_name_lower = category_name.lower().strip()
            
            # Skip header rows and subcategory headers
            if category_name_lower in ['', 'total', 'totals', 'expenses', 'program services', 'supporting services',
                                     'membership, meetings and education', 'standards development, pmo and tooling',
                                     'federal grant projects', 'management and general', 'membership development',
                                     'employee compensation', 'other expenses']:
                # Check if this is the final "Total expenses" row
                if 'total expenses' in category_name_lower or (category_name_lower == 'total' and i > len(functional_table) - 3):
                    # Extract overall totals
                    if year_total_col_idx and year_total_col_idx < len(row) and row[year_total_col_idx]:
                        try:
                            total_expenses = self._parse_amount(str(row[year_total_col_idx]))
                            # Try to extract program and supporting totals from this row
                            # They might be in program_total_col_idx and supporting_total_col_idx
                            if program_total_col_idx and program_total_col_idx < len(row) and row[program_total_col_idx]:
                                total_program_services = self._parse_amount(str(row[program_total_col_idx]))
                            if supporting_total_col_idx and supporting_total_col_idx < len(row) and row[supporting_total_col_idx]:
                                total_supporting_services = self._parse_amount(str(row[supporting_total_col_idx]))
                        except:
                            pass
                continue
            
            # Extract amounts for this category
            program_amount = 0.0
            supporting_amount = 0.0
            total_amount = 0.0
            
            # Get program total for this category
            if program_total_col_idx and program_total_col_idx < len(row) and row[program_total_col_idx]:
                try:
                    program_amount = self._parse_amount(str(row[program_total_col_idx]))
                except:
                    pass
            
            # Get supporting total for this category
            if supporting_total_col_idx and supporting_total_col_idx < len(row) and row[supporting_total_col_idx]:
                try:
                    supporting_amount = self._parse_amount(str(row[supporting_total_col_idx]))
                except:
                    pass
            
            # Get year total for this category (preferred over calculated)
            if year_total_col_idx and year_total_col_idx < len(row) and row[year_total_col_idx]:
                try:
                    total_amount = self._parse_amount(str(row[year_total_col_idx]))
                except:
                    # Fallback: calculate from program + supporting
                    total_amount = program_amount + supporting_amount
            else:
                # Calculate total from program + supporting
                total_amount = program_amount + supporting_amount
            
            # Only add category if it has a meaningful amount
            if total_amount > 0 or (program_amount > 0 and supporting_amount > 0):
                # Clean up category name
                category_name = re.sub(r'\s+', ' ', category_name).strip()
                
                categories.append(FunctionalExpenseCategory(
                    category_name=category_name,
                    program_services=max(0.0, program_amount),
                    supporting_services=max(0.0, supporting_amount),
                    total=total_amount
                ))
        
        # Calculate totals if not found
        if total_program_services == 0.0:
            total_program_services = sum(cat.program_services for cat in categories)
        if total_supporting_services == 0.0:
            total_supporting_services = sum(cat.supporting_services for cat in categories)
        
        total_expenses = total_program_services + total_supporting_services
        
        return FunctionalExpensesData(
            year=year,
            categories=categories,
            total_program_services=total_program_services,
            total_supporting_services=total_supporting_services,
            total_expenses=total_expenses
        )
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse an amount string to float, rounded to nearest whole number (nearest dollar)"""
        if not amount_str:
            return 0.0
        
        # Remove common formatting
        amount_str = amount_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
        # Handle empty or dash
        if not amount_str or amount_str == '-' or amount_str == '—':
            return 0.0
        
        try:
            # Round to nearest whole number (nearest dollar)
            return round(float(amount_str))
        except ValueError:
            return 0.0
    
    def _validate_revenue_totals(self, year_data: AuditedFinancialYearData):
        """Validate that revenue components sum to total revenue"""
        calculated_total = (
            year_data.program_service_revenue +
            year_data.contributions_grants +
            year_data.investment_income +
            year_data.other_revenue
        )
        
        difference = abs(year_data.total_revenue - calculated_total)
        if difference > self.tolerance:
            logger.warning(
                f"Year {year_data.year}: Revenue total mismatch. "
                f"Reported: ${year_data.total_revenue:,.2f}, "
                f"Calculated: ${calculated_total:,.2f}, "
                f"Difference: ${difference:,.2f}"
            )
    
    def _validate_functional_expenses(self, functional_expenses: FunctionalExpensesData, total_expenses: Optional[float]):
        """Validate that functional expenses sum correctly"""
        # Validate category totals
        for category in functional_expenses.categories:
            calculated_total = category.program_services + category.supporting_services
            difference = abs(category.total - calculated_total)
            if difference > self.tolerance:
                logger.warning(
                    f"Year {functional_expenses.year}: Category '{category.category_name}' total mismatch. "
                    f"Reported: ${category.total:,.2f}, "
                    f"Calculated: ${calculated_total:,.2f}, "
                    f"Difference: ${difference:,.2f}"
                )
        
        # Validate overall totals
        calculated_total = functional_expenses.total_program_services + functional_expenses.total_supporting_services
        difference = abs(functional_expenses.total_expenses - calculated_total)
        if difference > self.tolerance:
            logger.warning(
                f"Year {functional_expenses.year}: Functional expenses total mismatch. "
                f"Reported: ${functional_expenses.total_expenses:,.2f}, "
                f"Calculated: ${calculated_total:,.2f}, "
                f"Difference: ${difference:,.2f}"
            )
        
        # Validate against total expenses if provided
        if total_expenses:
            difference = abs(functional_expenses.total_expenses - total_expenses)
            if difference > self.tolerance:
                logger.warning(
                    f"Year {functional_expenses.year}: Functional expenses don't match total expenses. "
                    f"Total expenses: ${total_expenses:,.2f}, "
                    f"Functional expenses: ${functional_expenses.total_expenses:,.2f}, "
                    f"Difference: ${difference:,.2f}"
                )
    
    def _calculate_trends(self, financial_data: List[AuditedFinancialYearData]) -> List[FinancialTrend]:
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
    
    def _calculate_revenue_composition(self, financial_data: List[AuditedFinancialYearData]) -> List[RevenueComposition]:
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

