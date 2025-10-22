import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.models import (
    FinancialHealthMetrics, FinancialYearData, FinancialTrend, 
    RevenueComposition, FinancialChartData
)
from app.financial_parser import Form990Parser

class FinancialDataService:
    """Service for managing financial data from 990 forms"""
    
    def __init__(self, data_directory: str = "data/990s", cache_file: str = "data/processed/financial_data.json"):
        self.data_directory = data_directory
        self.cache_file = Path(cache_file)
        self.parser = Form990Parser(data_directory)
        self._cached_data = None
    
    def get_financial_health_metrics(self) -> FinancialHealthMetrics:
        """Get financial health metrics, using cache if available"""
        if self._cached_data is None:
            self._load_financial_data()
        return self._cached_data
    
    def _load_financial_data(self):
        """Load financial data from cache or parse XML files"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data_dict = json.load(f)
                self._cached_data = FinancialHealthMetrics(**data_dict)
                return
            except Exception as e:
                print(f"Error loading cached financial data: {e}")
        
        # Parse XML files if cache doesn't exist or is invalid
        self._cached_data = self.parser.parse_all_forms()
        self._save_financial_data()
    
    def _save_financial_data(self):
        """Save financial data to cache file"""
        if self._cached_data:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self._cached_data.dict(), f, indent=2)
    
    def refresh_financial_data(self):
        """Refresh financial data by re-parsing XML files"""
        self._cached_data = self.parser.parse_all_forms()
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
                    "tension": 0.4,  # Smooth curves
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Total Expenses", 
                    "data": expense_data,
                    "borderColor": "#ec2227",  # HL7 Red
                    "backgroundColor": "rgba(236, 34, 39, 0.1)",
                    "fill": False,
                    "tension": 0.4,  # Smooth curves
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
                    "backgroundColor": "#dc2626",  # WebAwesome Red
                    "stack": "revenue"
                },
                {
                    "label": "Contributions",
                    "data": contributions,
                    "backgroundColor": "#ca8a04",  # WebAwesome Yellow
                    "stack": "revenue"
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "backgroundColor": "#16a34a",  # WebAwesome Green
                    "stack": "revenue"
                },
                {
                    "label": "Other Revenue",
                    "data": other_revenue,
                    "backgroundColor": "#6b7280",  # WebAwesome Gray
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
                    "borderColor": "#dc2626",  # WebAwesome Red
                    "backgroundColor": "rgba(220, 38, 38, 0.1)",
                    "fill": False,
                    "tension": 0.4,  # Smooth curves
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Contributions",
                    "data": contributions,
                    "borderColor": "#ca8a04",  # WebAwesome Yellow
                    "backgroundColor": "rgba(202, 138, 4, 0.1)",
                    "fill": False,
                    "tension": 0.4,  # Smooth curves
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Investment Income",
                    "data": investment_income,
                    "borderColor": "#16a34a",  # WebAwesome Green
                    "backgroundColor": "rgba(22, 163, 74, 0.1)",
                    "fill": False,
                    "tension": 0.4,  # Smooth curves
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
        
        # Add management services for pre-2024 years
        management_services = []
        for year in metrics.years:
            if year.management_services is not None:
                management_services.append(year.management_services)
            else:
                management_services.append(0)
        
        datasets = [
            {
                "label": "Salaries & Compensation",
                "data": salaries,
                "backgroundColor": "#dc2626",  # WebAwesome Red
                "stack": "expenses"
            },
            {
                "label": "Other Expenses",
                "data": other_expenses,
                "backgroundColor": "#6b7280",  # WebAwesome Gray
                "stack": "expenses"
            }
        ]
        
        # Add management services if any data exists
        if any(ms > 0 for ms in management_services):
            datasets.append({
                "label": "Management Services (Pre-2024)",
                "data": management_services,
                "backgroundColor": "#ea580c",  # WebAwesome Orange
                "stack": "expenses"
            })
        
        return FinancialChartData(
            labels=years,
            datasets=datasets,
            type="bar",
            title="Expense Breakdown"
        )
    
    def get_program_service_breakdown_chart(self) -> FinancialChartData:
        """Get chart data for program service revenue breakdown"""
        metrics = self.get_financial_health_metrics()
        
        years = [str(year.year) for year in metrics.years]
        membership_dues = [year.membership_dues or 0 for year in metrics.years]
        meetings = [year.meetings_conferences or 0 for year in metrics.years]
        education = [year.education_certification or 0 for year in metrics.years]
        project_management = [year.project_management_fees or 0 for year in metrics.years]
        sponsorship = [year.qualified_sponsorship_payments or 0 for year in metrics.years]
        other_services = [year.other_program_services or 0 for year in metrics.years]
        
        return FinancialChartData(
            labels=years,
            datasets=[
                {
                    "label": "Membership Dues",
                    "data": membership_dues,
                    "borderColor": "#dc2626",  # WebAwesome Red
                    "backgroundColor": "rgba(220, 38, 38, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Meetings & Conferences",
                    "data": meetings,
                    "borderColor": "#ca8a04",  # WebAwesome Yellow
                    "backgroundColor": "rgba(202, 138, 4, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Education & Certification",
                    "data": education,
                    "borderColor": "#16a34a",  # WebAwesome Green
                    "backgroundColor": "rgba(22, 163, 74, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Project Management Fees",
                    "data": project_management,
                    "borderColor": "#ea580c",  # WebAwesome Orange
                    "backgroundColor": "rgba(234, 88, 12, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Sponsorship Payments",
                    "data": sponsorship,
                    "borderColor": "#5f9baf",  # Light Blue
                    "backgroundColor": "rgba(95, 155, 175, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                },
                {
                    "label": "Other Program Services",
                    "data": other_services,
                    "borderColor": "#6b7280",  # WebAwesome Gray
                    "backgroundColor": "rgba(107, 114, 128, 0.1)",
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointHoverRadius": 6
                }
            ],
            type="line",
            title="Program Service Revenue Breakdown"
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
            # Net income improvement: better if deficit is smaller or if we go from deficit to surplus
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
            "total_employees": latest_year.total_employees,
            "total_volunteers": latest_year.total_volunteers,
            "years_available": metrics.years_available
        }
    
    def generate_llm_prompt(self, output_file: str = "data/processed/llm_prompt.txt") -> str:
        """Generate a comprehensive prompt for LLM analysis of financial data"""
        metrics = self.get_financial_health_metrics()
        
        # Build comprehensive financial data text
        prompt_text = f"""# HL7 International Financial Analysis Request

## Organization Context
HL7 International is a non-profit organization focused on healthcare interoperability standards. 

### Key Organizational Changes:
- **April 2013**: **MAJOR BUSINESS MODEL CHANGE** - HL7 decided to make its standards, domain analysis models, profiles and implementation guides available at no cost to all. Previously, access to these standards required being an HL7 member. This date marks a substantial change in the HL7 business model and significantly impacts revenue analysis.
- **2022**: Major restructuring - created two divisions (Standards Development and Standards Implementation) and hired three executives: Daniel Vreeman (Chief Standards Development Officer), Viet Nguyen (Chief Standards Implementation Officer), and Diego Kaminker (Deputy Chief Standards Implementation Officer)
- **2023**: Purchased AMG LLC, which significantly impacted their financial structure as AMG staff became HL7 employees

## Financial Data Analysis Request

Please analyze the following financial data and provide a structured assessment with both positive developments and critical concerns. Format your response as markdown with two main sections:

1. **Critical Financial Concerns** - Issues that need attention
2. **Positive Developments** - Areas showing improvement or strength

## Financial Data (2014-2024)

### Year-over-Year Summary
"""
        
        # Add year-by-year summary
        for year_data in metrics.years:
            prompt_text += f"""
**{year_data.year}:**
- Total Revenue: ${year_data.total_revenue:,.0f}
- Total Expenses: ${year_data.total_expenses:,.0f}
- Net Income: ${year_data.net_income:,.0f}
- Net Assets: ${year_data.net_assets:,.0f}
- Employees: {year_data.total_employees}
- Program Service Revenue: ${year_data.program_service_revenue:,.0f}
  - Membership Dues: ${year_data.membership_dues or 0:,.0f}
  - Meetings & Conferences: ${year_data.meetings_conferences or 0:,.0f}
  - Education & Certification: ${year_data.education_certification or 0:,.0f}
  - Project Management Fees: ${year_data.project_management_fees or 0:,.0f}
  - Other Program Services: ${year_data.other_program_services or 0:,.0f}
- Contributions & Grants: ${year_data.contributions_grants:,.0f}
- Investment Income: ${year_data.investment_income:,.0f}
- Salaries & Compensation: ${year_data.salaries_compensation:,.0f}
- Other Expenses: ${year_data.other_expenses:,.0f}
"""
            if year_data.management_services:
                prompt_text += f"- Management Services: ${year_data.management_services:,.0f}\n"
        
        prompt_text += f"""

## Key Context for Analysis

### Major Business Model Change (April 2013)
- **Critical Context**: In April 2013, HL7 made a fundamental change to its business model by making all standards freely available to everyone, not just members
- **Revenue Impact**: This change likely had significant impact on membership value proposition and revenue streams
- **Analysis Consideration**: When analyzing pre-2013 vs post-2013 data, consider how this change affected membership growth, retention, and alternative revenue development
- **Strategic Context**: This change aligns with HL7's current 2025+ strategic vision for revenue diversification, as it represents an early move away from membership-dependent access models

### AMG LLC Acquisition Impact (2023-2024)
- In 2023, HL7 purchased AMG LLC for $3.3M in management services expenses
- In 2024, AMG staff became HL7 employees, shifting from external management services to internal salaries
- This structural change affects year-over-year comparisons

### Revenue Streams Analysis
- **Program Services** (primary revenue): Membership dues, meetings, education, project management
- **Contributions & Grants**: Primarily government funding
- **Investment Income**: Market-dependent returns
- **Other Revenue**: Miscellaneous sources

### Expense Categories
- **Salaries & Compensation**: Employee costs (includes former AMG staff in 2024)
- **Other Expenses**: Operational costs, facilities, etc.
- **Management Services**: Pre-2024 external AMG services

## 2025+ HL7 Strategic Vision: Revenue Diversification Strategies

### Revenue Diversification Goals
HL7 is actively working to develop initiatives that boost revenue from non-membership sources. This includes:
- **Global Market Expansion**: Exploring new global markets and opportunities that align with HL7's mission and capabilities
- **Channel Optimization**: Optimizing existing revenue channels for better performance
- **New Partnership Development**: Building and securing new partnerships and collaborations that advance HL7's mission while creating additional revenue streams

### New Market Offerings
HL7 plans to develop a dedicated program to incubate and pilot new revenue-generating ideas and partnerships:
- **Product Development**: Introducing new products, services, or offerings that address market needs
- **Strategic Alignment**: Ensuring new offerings align with HL7's strategic goals and mission
- **Innovation Pipeline**: Creating structured processes for evaluating and implementing new revenue opportunities

### External Funding and Strategic Opportunities
- **Funding Opportunity Capture**: Increasing the number of successful funding opportunities pursued and acquired
- **Capability Building**: Developing processes for successful capture, including pipeline management, proposal development, and partnership strategies
- **Strategic Opportunity Management**: Reducing instances where strategic opportunities are missed due to inability to capture them
- **Structured Approach**: Developing systematic methods to secure strategic work

### Strategic Impact
By focusing on these diversification strategies, HL7 intends to:
- **Strengthen Financial Foundation**: Enable growth and innovation while reducing reliance on membership dues
- **Mission Support**: Support HL7's mission to improve health care standards globally
- **Long-term Sustainability**: Create a more robust and diversified revenue model

## Analysis Requirements

Please provide insights on:

1. **Financial Health Trends**: Multi-year patterns in revenue, expenses, and net income, with special attention to the impact of the April 2013 business model change
2. **Revenue Diversification**: Stability and growth of different revenue streams, with specific attention to HL7's strategic goals for reducing reliance on membership dues and how the 2013 standards access change affected this
3. **Expense Management**: Efficiency and cost control measures
4. **Asset Management**: Net asset trends and financial stability
5. **Business Model Evolution**: How the 2013 change to free standards access affected membership value proposition and revenue development over time
6. **Strategic Implications**: Recommendations for financial sustainability that align with HL7's 2025+ strategic vision for revenue diversification
7. **Strategic Alignment**: How current financial performance supports or challenges the organization's goals for new market offerings, partnerships, and external funding opportunities

## Output Format

**IMPORTANT: Your response must be formatted as a complete markdown file that can be saved directly as `financial_insights.md`.**

Structure your response as a markdown document with the following format:

```markdown
# HL7 International Financial Analysis - 2024

## Critical Financial Concerns

### [Concern Title]
- **Specific Issue**: [Detailed description with data points]
- **Impact**: [Quantified impact with percentages and dollar amounts]
- **Trend**: [Multi-year trend analysis with specific metrics]

### [Another Concern Title]
- **Specific Issue**: [Detailed description with data points]
- **Impact**: [Quantified impact with percentages and dollar amounts]
- **Trend**: [Multi-year trend analysis with specific metrics]

## Positive Developments

### [Positive Development Title]
- **Achievement**: [Specific accomplishment with data points]
- **Growth**: [Quantified growth with percentages and dollar amounts]
- **Comparison**: [Year-over-year comparison with specific metrics]

### [Another Positive Development Title]
- **Achievement**: [Specific accomplishment with data points]
- **Growth**: [Quantified growth with percentages and dollar amounts]
- **Comparison**: [Year-over-year comparison with specific metrics]

## Strategic Recommendations

1. **[Revenue Diversification Recommendation]**: [Specific advice aligned with HL7's strategic vision for reducing membership dues reliance]
2. **[Partnership & Funding Recommendation]**: [Specific advice for new partnerships and external funding opportunities]
3. **[Market Development Recommendation]**: [Specific advice for new market offerings and global expansion]
4. **[Financial Sustainability Recommendation]**: [Specific advice for long-term financial health and mission support]
```

**Formatting Requirements:**
- Use proper markdown headers (`#`, `##`, `###`)
- Use bullet points with `-` for lists
- Use **bold text** for emphasis on key metrics
- Include specific dollar amounts, percentages, and year-over-year comparisons
- Focus on actionable insights valuable for organizational leadership
- Ensure the output is a complete, standalone markdown document
"""
        
        # Save prompt to file
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(prompt_text)
        
        return prompt_text
    
    def parse_markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown content to styled HTML using WebAwesome theme"""
        
        # Split content into lines for processing
        lines = markdown_content.split('\n')
        html_lines = []
        in_list = False
        list_type = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                html_lines.append('')
                continue
            
            # Headers
            if line.startswith('### '):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                title = line[4:].strip()
                html_lines.append(f'<h3 class="insight-section-title">{title}</h3>')
                
            elif line.startswith('## '):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                title = line[3:].strip()
                html_lines.append(f'<h2 class="insight-main-title">{title}</h2>')
                
            elif line.startswith('# '):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                title = line[2:].strip()
                # Check if this is the main document title
                if "AI-Generated" in title or "Financial Analysis" in title:
                    html_lines.append(f'<h1 class="insight-document-title">{title}</h1>')
                else:
                    html_lines.append(f'<h1 class="insight-document-title">{title}</h1>')
            
            # Horizontal rules
            elif line.startswith('---') or line.startswith('***') or line.startswith('___'):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                html_lines.append('<hr class="insight-hr">')
            
            # Lists
            elif line.startswith('- '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    html_lines.append('<ul class="insight-list">')
                    in_list = True
                    list_type = 'ul'
                
                # Parse bold text and regular text
                content = line[2:].strip()
                content = self._parse_inline_formatting(content)
                html_lines.append(f'<li class="insight-list-item">{content}</li>')
                
            elif re.match(r'^\d+\. ', line):
                if not in_list or list_type != 'ol':
                    if in_list:
                        html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    html_lines.append('<ol class="insight-list">')
                    in_list = True
                    list_type = 'ol'
                
                # Parse numbered list item
                content = re.sub(r'^\d+\. ', '', line).strip()
                content = self._parse_inline_formatting(content)
                html_lines.append(f'<li class="insight-list-item">{content}</li>')
            
            # Regular paragraphs
            else:
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                    in_list = False
                    list_type = None
                
                if line:
                    content = self._parse_inline_formatting(line)
                    html_lines.append(f'<p class="insight-paragraph">{content}</p>')
        
        # Close any open lists
        if in_list:
            html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
        
        return '\n'.join(html_lines)
    
    def _parse_inline_formatting(self, text: str) -> str:
        """Parse inline markdown formatting (bold, etc.)"""
        # Bold text **text**
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="insight-bold">\1</strong>', text)
        
        # Italic text *text*
        text = re.sub(r'\*(.*?)\*', r'<em class="insight-italic">\1</em>', text)
        
        # Code text `text`
        text = re.sub(r'`(.*?)`', r'<code class="insight-code">\1</code>', text)
        
        return text
    
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
                    "name": "Contributions",
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
                    "change": None  # N/A for net income
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
