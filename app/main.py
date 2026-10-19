from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.requests import Request
from typing import List, Optional
import os
import logging
import re
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import shutil

logger = logging.getLogger(__name__)

from app.models import KPICard, KPISummary, KPIFilter, ChartData, DashboardMetrics, KPIIndicator, FinancialHealthMetrics, FinancialChartData, AuditedFinancialHealthMetrics, ConsolidatedFinancialData
from app.data_service import DataService
from app.audited_financials_service import AuditedFinancialsService
from app.consolidated_financial_service import ConsolidatedFinancialService
from app.financial_data_editor_service import FinancialDataEditorService
from app.geographic_financial_service import GeographicFinancialService
from app.published_standards_service import PublishedStandardsService
from app.meeting_locations_service import MeetingLocationsService
from app.standards_development_prompt_service import (
    StandardsDevelopmentPromptRequest,
    StandardsDevelopmentPromptService,
)
from app.wg_health_history_service import WgHealthHistoryService
from app.wg_portfolio_matrices_service import WgPortfolioMatricesService
from app.wg_meeting_participation_service import WgMeetingParticipationService

# Load environment variables
load_dotenv()

app = FastAPI(
    title="HL7 KPI Dashboard",
    description="Company dashboard for displaying KPIs and key metrics",
    version="1.0.0"
)

# Initialize data services
data_service = DataService()
audited_financials_service = AuditedFinancialsService()
consolidated_financial_service = ConsolidatedFinancialService()
financial_data_editor_service = FinancialDataEditorService()
geographic_financial_service = GeographicFinancialService()
published_standards_service = PublishedStandardsService()
meeting_locations_service = MeetingLocationsService()
standards_development_prompt_service = StandardsDevelopmentPromptService(
    data_service,
    meeting_locations_service,
    published_standards_service,
)
wg_health_history_service = WgHealthHistoryService()
wg_portfolio_matrices_service = WgPortfolioMatricesService()
wg_meeting_participation_service = WgMeetingParticipationService()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Environment variables for WebAwesome
WEBAWESOME_KEY = os.getenv("WEBAWESOME_KEY", "")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - shows HL7 International indicators by default"""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "steward": "HL7 International"
        }
    )

@app.get("/csdo", response_class=HTMLResponse)
async def csdo_dashboard(request: Request):
    """CSDO dashboard page"""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "steward": "CSDO"
        }
    )

@app.get("/api/kpi-cards")
async def get_kpi_cards(
    steward: Optional[str] = Query(None, description="Filter by steward"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    kpi_only: bool = Query(False, description="Show only KPI-designated indicators"),
    tag_filter: Optional[str] = Query(None, description="Filter by specific tag")
):
    """Get KPI cards with optional filtering"""
    try:
        return data_service.get_kpi_cards(steward=steward, domain=domain, kpi_only=kpi_only, tag_filter=tag_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/indicators", response_model=List[KPIIndicator])
async def get_indicators(
    steward: Optional[str] = Query(None, description="Filter by steward"),
    domain: Optional[str] = Query(None, description="Filter by domain")
):
    """Get KPI indicators with optional filtering"""
    try:
        if steward:
            return data_service.get_indicators_by_steward(steward)
        elif domain:
            return data_service.get_indicators_by_domain(domain)
        else:
            kpi_data = data_service.get_kpi_data()
            return list(kpi_data.indicators.values()) if kpi_data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/indicators/{indicator_id}", response_model=KPIIndicator)
async def get_indicator(indicator_id: str):
    """Get a specific indicator by ID"""
    try:
        indicator = data_service.get_indicator_by_id(indicator_id)
        if not indicator:
            raise HTTPException(status_code=404, detail="Indicator not found")
        return indicator
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary", response_model=KPISummary)
async def get_kpi_summary(
    steward: Optional[str] = Query(None, description="Filter by steward"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tag_filter: Optional[str] = Query(None, description="Filter by specific tag")
):
    """Get KPI summary statistics with optional filtering"""
    try:
        return data_service.get_kpi_summary(steward=steward, domain=domain, tag_filter=tag_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/{chart_type}", response_model=ChartData)
async def get_chart_data(
    chart_type: str,
    steward: Optional[str] = Query(None, description="Filter by steward")
):
    """Get chart data for different visualizations"""
    try:
        return data_service.get_chart_data(chart_type, steward=steward)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard", response_model=DashboardMetrics)
async def get_dashboard_data(steward: Optional[str] = Query(None, description="Filter by steward")):
    """Get complete dashboard data"""
    try:
        return data_service.get_dashboard_metrics(steward=steward)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metadata")
async def get_metadata():
    """Get data metadata"""
    try:
        metadata = data_service.get_metadata()
        if not metadata:
            raise HTTPException(status_code=404, detail="Metadata not found")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stewards")
async def get_stewards():
    """Get all available stewards for navigation"""
    try:
        metadata = data_service.get_metadata()
        if not metadata:
            return []
        return metadata.stewards
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Financial Health Dashboard Endpoints - Using Audited Financials as Primary Source
@app.get("/financial-health", response_class=HTMLResponse)
async def financial_health_dashboard(request: Request):
    """Financial health dashboard page - Using Audited Financial Statements"""
    return templates.TemplateResponse(
        "finance_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Financial Health Dashboard"
        }
    )

@app.get("/api/financial/health", response_model=FinancialHealthMetrics)
async def get_financial_health():
    """Get financial health metrics from audited financial statements (primary source)"""
    try:
        return consolidated_financial_service.get_financial_health_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/summary")
async def get_financial_summary():
    """Get financial summary statistics from audited financial statements (primary source)"""
    try:
        return consolidated_financial_service.get_financial_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/charts/{chart_type}", response_model=FinancialChartData)
async def get_financial_chart(chart_type: str):
    """Get financial chart data from audited financial statements (primary source)"""
    try:
        if chart_type == "revenue-expense-trend":
            return consolidated_financial_service.get_revenue_expense_trend_chart()
        elif chart_type == "revenue-composition":
            return consolidated_financial_service.get_revenue_composition_chart()
        elif chart_type == "revenue-composition-relative":
            return consolidated_financial_service.get_revenue_composition_relative_chart()
        elif chart_type == "key-revenue-streams":
            return consolidated_financial_service.get_key_revenue_streams_chart()
        elif chart_type == "expense-breakdown":
            return consolidated_financial_service.get_expense_breakdown_chart()
        elif chart_type == "program-service-breakdown":
            return consolidated_financial_service.get_program_service_breakdown_chart()
        elif chart_type == "detailed-expense-trends":
            return consolidated_financial_service.get_audited_detailed_functional_expenses_chart()
        elif chart_type == "detailed-expense-trends-program":
            return consolidated_financial_service.get_audited_detailed_functional_expenses_chart(service_type="program")
        elif chart_type == "detailed-expense-trends-supporting":
            return consolidated_financial_service.get_audited_detailed_functional_expenses_chart(service_type="supporting")
        elif chart_type == "revenue-expense-comparison":
            return consolidated_financial_service.get_revenue_expense_comparison_chart()
        elif chart_type == "program-services-revenue-expense-trend":
            return consolidated_financial_service.get_program_services_revenue_expense_trend_chart()
        elif chart_type == "operating-reserve":
            return consolidated_financial_service.get_operating_reserve_chart()
        else:
            raise HTTPException(status_code=404, detail="Chart type not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/financial/refresh")
async def refresh_financial_data():
    """Refresh financial data by re-parsing audited financial PDFs and updating consolidated data"""
    try:
        # Refresh audited financials (primary source)
        audited_financials_service.refresh_financial_data()
        # Update consolidated data
        consolidated_financial_service.refresh_consolidated_data()
        return {
            "status": "success",
            "message": "Financial data refreshed successfully from audited financial statements"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing financial data: {str(e)}")

@app.get("/api/financial/detailed-table")
async def get_detailed_financial_table():
    """Get detailed financial data table from audited financial statements (primary source)"""
    try:
        table_data = consolidated_financial_service.get_detailed_financial_table()
        return table_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading detailed table: {str(e)}")


# Audited Financials Dashboard Endpoints
@app.get("/financial-health-audited", response_class=HTMLResponse)
async def audited_financial_health_dashboard(request: Request):
    """Financial health dashboard page - Audited Financials"""
    return templates.TemplateResponse(
        "audited_finance_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Financial Health Dashboard - Audited Financials"
        }
    )

@app.get("/api/audited-financial/health", response_model=AuditedFinancialHealthMetrics)
async def get_audited_financial_health():
    """Get financial health metrics from audited financial statements (from consolidated data)"""
    try:
        return consolidated_financial_service.get_audited_financial_health_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audited-financial/summary")
async def get_audited_financial_summary():
    """Get financial summary statistics from audited financial statements (from consolidated data)"""
    try:
        return consolidated_financial_service.get_audited_financial_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audited-financial/charts/{chart_type}", response_model=FinancialChartData)
async def get_audited_financial_chart(chart_type: str):
    """Get financial chart data from audited financial statements (from consolidated data)"""
    try:
        if chart_type == "revenue-expense-trend":
            return consolidated_financial_service.get_audited_revenue_expense_trend_chart()
        elif chart_type == "revenue-composition":
            return consolidated_financial_service.get_audited_revenue_composition_chart()
        elif chart_type == "key-revenue-streams":
            return consolidated_financial_service.get_audited_key_revenue_streams_chart()
        elif chart_type == "expense-breakdown":
            return consolidated_financial_service.get_audited_expense_breakdown_chart()
        elif chart_type == "functional-expenses":
            return consolidated_financial_service.get_audited_functional_expenses_chart()
        elif chart_type == "detailed-functional-expenses":
            return consolidated_financial_service.get_audited_detailed_functional_expenses_chart()
        else:
            raise HTTPException(status_code=404, detail="Chart type not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audited-financial/refresh")
async def refresh_audited_financial_data():
    """Refresh audited financial data by re-parsing PDF files and updating consolidated data"""
    try:
        # Refresh the underlying audited financials service (parses PDFs)
        audited_financials_service.refresh_financial_data()
        # Refresh consolidated data to pick up the new audited data
        consolidated_financial_service.refresh_consolidated_data()
        return {
            "status": "success",
            "message": "Audited financial data refreshed successfully and consolidated data updated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing audited financial data: {str(e)}")

@app.get("/api/audited-financial/detailed-table")
async def get_audited_detailed_financial_table():
    """Get detailed financial data table from audited financial statements (from consolidated data)"""
    try:
        table_data = consolidated_financial_service.get_audited_detailed_financial_table()
        return table_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading detailed table: {str(e)}")

# Consolidated Financial Data Endpoints
@app.get("/api/consolidated-financial/data", response_model=ConsolidatedFinancialData)
async def get_consolidated_financial_data():
    """Get consolidated financial data from audited financial statements and budgets"""
    try:
        return consolidated_financial_service.get_consolidated_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/consolidated-financial/year/{year}")
async def get_consolidated_financial_year(year: int):
    """Get consolidated financial data for a specific year"""
    try:
        consolidated_data = consolidated_financial_service.get_consolidated_data()
        year_data = consolidated_data.get_year(year)
        if not year_data:
            raise HTTPException(status_code=404, detail=f"No data found for year {year}")
        return year_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/consolidated-financial/budget-vs-actual")
async def get_budget_vs_actual_chart(year: Optional[int] = Query(None, description="Specific year, or all years if not provided")):
    """Get chart data comparing budget vs actual"""
    try:
        chart_data = consolidated_financial_service.get_budget_vs_actual_chart(year=year)
        return chart_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/consolidated-financial/refresh")
async def refresh_consolidated_financial_data():
    """Refresh consolidated financial data by rebuilding from all sources"""
    try:
        consolidated_financial_service.refresh_consolidated_data()
        return {
            "status": "success",
            "message": "Consolidated financial data refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing consolidated data: {str(e)}")

# Financial Data Editor Endpoints
@app.get("/financial-data-editor", response_class=HTMLResponse)
async def financial_data_editor(request: Request):
    """Financial data editor page for reviewing and editing financial data"""
    return templates.TemplateResponse(
        "financial_data_editor.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY
        }
    )

@app.get("/api/financial-editor/years")
async def get_editor_years():
    """Get list of available years for editing"""
    try:
        data = financial_data_editor_service.load_data()
        return sorted([y.year for y in data.years])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial-editor/year/{year}")
async def get_editor_year_data(year: int):
    """Get data for a specific year for editing"""
    try:
        year_data = financial_data_editor_service.get_year_data(year)
        if not year_data:
            raise HTTPException(status_code=404, detail=f"No data found for year {year}")
        return year_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/financial-editor/year/{year}")
async def create_or_update_year(year: int, year_data: dict):
    """Create or update year data"""
    try:
        updated_year = financial_data_editor_service.create_or_update_year(year, year_data)
        return updated_year
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/financial-editor/year/{year}/audited/{field_name}")
async def update_audited_field(year: int, field_name: str, update_data: dict):
    """Update a single audited field"""
    try:
        value = update_data.get("value")
        updated_year = financial_data_editor_service.update_audited_field(year, field_name, value)
        return updated_year
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/financial-editor/year/{year}/budget/{version}/{field_name}")
async def update_budget_field(year: int, version: str, field_name: str, update_data: dict):
    """Update a single budget field (draft or final)"""
    try:
        if version not in ["draft", "final"]:
            raise HTTPException(status_code=400, detail="Version must be 'draft' or 'final'")
        value = update_data.get("value")
        updated_year = financial_data_editor_service.update_budget_field(year, version, field_name, value)
        return updated_year
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/financial-editor/year/{year}/functional-expense/{category_name:path}")
async def update_functional_expense(year: int, category_name: str, update_data: dict):
    """Update a functional expense category"""
    try:
        # URL decode the category name
        from urllib.parse import unquote
        decoded_category_name = unquote(category_name)
        updated_year = financial_data_editor_service.update_functional_expense_category(
            year,
            decoded_category_name,
            program_services=update_data.get("program_services"),
            supporting_services=update_data.get("supporting_services"),
            total=update_data.get("total"),
            membership_meetings_education=update_data.get("membership_meetings_education"),
            standards_development_pmo_tooling=update_data.get("standards_development_pmo_tooling"),
            federal_grant_projects=update_data.get("federal_grant_projects"),
            management_general=update_data.get("management_general"),
            membership_development=update_data.get("membership_development")
        )
        return updated_year
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial-editor/structure")
async def get_editable_structure():
    """Get data in a structure optimized for editing UI"""
    try:
        return financial_data_editor_service.get_editable_data_structure()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/financial-editor/import-from-pdfs")
async def import_from_pdfs():
    """Import initial data from PDF parsing (one-time operation)"""
    try:
        data = financial_data_editor_service.import_from_audited_service()
        return {
            "status": "success",
            "message": f"Imported data for {len(data.years)} years from PDFs",
            "years": data.years_available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/llm-prompt")
async def generate_llm_prompt():
    """Generate LLM prompt with financial data for analysis"""
    try:
        result = consolidated_financial_service.generate_llm_prompt()
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generating LLM prompt: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error generating LLM prompt: {str(e)}")

# Geographic Financial Dashboard Endpoints
@app.get("/financial-geographic", response_class=HTMLResponse)
async def financial_geographic_dashboard(request: Request):
    """Financial Health - Geographic Insights dashboard page"""
    return templates.TemplateResponse(
        "financial_geographic_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Financial Health - Geographic Insights"
        }
    )

@app.get("/api/geographic-financial/key-indicators")
async def get_geographic_key_indicators(year: Optional[int] = Query(None, description="Year (optional, defaults to latest)")):
    """Get key indicators for geographic financial dashboard"""
    try:
        return geographic_financial_service.get_key_indicators(year=year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/geographic-financial/country-data")
async def get_geographic_country_data(
    year: Optional[int] = Query(None, description="Year (optional, defaults to latest)"),
    data_type: str = Query("combined", description="Data type: 'membership', 'affiliate', or 'combined'")
):
    """Get country data for map visualization"""
    try:
        if data_type not in ["membership", "affiliate", "combined"]:
            raise HTTPException(status_code=400, detail="data_type must be 'membership', 'affiliate', or 'combined'")
        return geographic_financial_service.get_country_data_for_map(year=year, data_type=data_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/geographic-financial/years")
async def get_geographic_years():
    """Get available years for geographic financial data"""
    try:
        metrics = geographic_financial_service.get_geographic_metrics()
        return {"years": metrics.years_available, "latest_year": metrics.latest_year}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/geographic-financial/refresh")
async def refresh_geographic_financial_data():
    """Refresh geographic financial data by re-parsing Excel file"""
    try:
        geographic_financial_service.refresh_financial_data()
        return {
            "status": "success",
            "message": "Geographic financial data refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing geographic financial data: {str(e)}")

# Geographic Financial CRUD Endpoints
@app.get("/api/geographic-financial/countries")
async def get_geographic_countries(year: Optional[int] = Query(None, description="Year (optional, defaults to latest)")):
    """Get all countries with their revenue data for a specific year"""
    try:
        countries = geographic_financial_service.get_countries_for_year(year=year)
        return countries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/geographic-financial/countries/{country}")
async def update_geographic_country(
    country: str,
    year: int = Query(..., description="Year"),
    membership_revenue: Optional[float] = Query(None, description="Membership revenue"),
    affiliate_revenue: Optional[float] = Query(None, description="Affiliate revenue")
):
    """Update revenue for a country"""
    try:
        from urllib.parse import unquote
        # Decode URL-encoded country name
        country = unquote(country)
        
        if membership_revenue is None and affiliate_revenue is None:
            raise HTTPException(status_code=400, detail="At least one revenue value must be provided")
        
        result = geographic_financial_service.update_country_revenue(
            year=year,
            country=country,
            membership_revenue=membership_revenue,
            affiliate_revenue=affiliate_revenue
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/geographic-financial/countries")
async def add_geographic_country(
    country: str = Query(..., description="Country name"),
    year: int = Query(..., description="Year"),
    membership_revenue: float = Query(0.0, description="Membership revenue"),
    affiliate_revenue: float = Query(0.0, description="Affiliate revenue")
):
    """Add a new country with revenue data"""
    try:
        result = geographic_financial_service.add_country(
            year=year,
            country=country,
            membership_revenue=membership_revenue,
            affiliate_revenue=affiliate_revenue
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/geographic-financial/countries/{country}")
async def delete_geographic_country(
    country: str,
    year: int = Query(..., description="Year")
):
    """Delete a country (remove it from the data)"""
    try:
        from urllib.parse import unquote
        # Decode URL-encoded country name
        country = unquote(country)
        
        result = geographic_financial_service.delete_country(year=year, country=country)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/geographic-financial/import-excel")
async def import_geographic_from_excel():
    """Import data from Excel file (legacy endpoint)"""
    try:
        result = geographic_financial_service.import_from_excel()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/geographic-financial/import-file")
async def import_geographic_from_file(
    file: UploadFile = File(...),
    year: int = Form(...),
    revenue_type: str = Form(...),
    fresh_load: bool = Form(False)
):
    """Import geographic revenue data from uploaded CSV or Excel file"""
    if revenue_type not in ['membership', 'affiliate']:
        raise HTTPException(status_code=400, detail="revenue_type must be 'membership' or 'affiliate'")
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ''
    if file_ext not in ['.csv', '.xlsx', '.xls']:
        raise HTTPException(status_code=400, detail="File must be CSV or Excel format (.csv, .xlsx, .xls)")
    
    # Save uploaded file to temporary location
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file = Path(tmp.name)
        
        # Parse the file
        parser = geographic_financial_service.parser
        revenue_by_country, unmatched_countries = parser.parse_file_intelligent(temp_file, revenue_type, year)
        
        # If fresh load, clear existing values for this revenue type in this year
        if fresh_load:
            metrics = geographic_financial_service.get_geographic_metrics()
            year_data = metrics.get_year(year)
            if year_data:
                for country_data in year_data.countries.values():
                    if revenue_type == 'membership':
                        country_data.membership_revenue = 0.0
                    else:
                        country_data.affiliate_revenue = 0.0
                # Save cleared values before importing new ones
                geographic_financial_service.save_to_cache()
        
        # Update the data
        updated_countries = []
        for country, revenue in revenue_by_country.items():
            # Log for debugging special cases
            if country in ['Taiwan, China', 'Central America and Dominican Republic', 'Other (International Affiliates)']:
                logger.info(f"Importing {country}: {revenue_type} revenue = {revenue}")
            
            result = geographic_financial_service.update_country_revenue(
                year=year,
                country=country,
                membership_revenue=revenue if revenue_type == 'membership' else None,
                affiliate_revenue=revenue if revenue_type == 'affiliate' else None
            )
            
            # Log the result for debugging
            if country in ['Taiwan, China', 'Central America and Dominican Republic', 'Other (International Affiliates)']:
                logger.info(f"After update {country}: membership={result.get('membership_revenue')}, affiliate={result.get('affiliate_revenue')}")
            
            updated_countries.append(country)
        
        # Save to cache
        geographic_financial_service.save_to_cache()
        
        return {
            "status": "success",
            "message": f"Imported {len(updated_countries)} countries from {file.filename}",
            "year": year,
            "revenue_type": revenue_type,
            "fresh_load": fresh_load,
            "countries_count": len(updated_countries),
            "countries": updated_countries[:10],  # First 10 for preview
            "unmatched_countries": unmatched_countries
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing file: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file and temp_file.exists():
            temp_file.unlink()

@app.post("/api/geographic-financial/save")
async def save_geographic_to_cache():
    """Save current data to cache file"""
    try:
        result = geographic_financial_service.save_to_cache()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Membership Health Dashboard Endpoints
@app.get("/membership-health", response_class=HTMLResponse)
async def membership_health_dashboard(request: Request):
    """Membership health dashboard page"""
    return templates.TemplateResponse(
        "membership_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Membership Health Dashboard"
        }
    )

# Standards Development Insights Dashboard Endpoints
@app.get("/standards-development-insights", response_class=HTMLResponse)
async def standards_development_insights_dashboard(request: Request):
    """Standards Development Insights dashboard page"""
    return templates.TemplateResponse(
        "standards_development_insights_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Standards Development Insights"
        }
    )

@app.get("/wg-health-history", response_class=HTMLResponse)
async def wg_health_history_dashboard(request: Request):
    """Legacy Final Work Group Health scorecard history"""
    return templates.TemplateResponse(
        "wg_health_history_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Work Group Health History",
        },
    )

@app.get("/wg-meeting-participation", response_class=HTMLResponse)
async def wg_meeting_participation_dashboard(request: Request):
    """Meeting attendance / people signals from Confluence minutes"""
    return templates.TemplateResponse(
        "wg_meeting_participation_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY,
            "dashboard_title": "Meeting Participation",
        },
    )

@app.get("/api/standards-development/wg-health-history")
async def get_wg_health_history_overview():
    """Portfolio heatmap + cycle/work group indexes for Final WGH history"""
    try:
        return wg_health_history_service.get_overview()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/wg-health-history/cycles/{cycle}")
async def get_wg_health_history_cycle(cycle: str):
    """All work groups for one Final WGH cycle"""
    try:
        return wg_health_history_service.get_cycle(cycle)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/wg-health-history/workgroups/{wg_key}")
async def get_wg_health_history_workgroup(wg_key: str):
    """One work group across all Final WGH cycles"""
    try:
        return wg_health_history_service.get_workgroup(wg_key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/wg-health-history/validation")
async def get_wg_health_history_validation():
    """Machine-readable validation report for the Final WGH extract"""
    try:
        return wg_health_history_service.get_validation()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/fhir-resource-ownership-matrix")
async def get_fhir_resource_ownership_matrix():
    """FHIR base resources owned by work group across FHIR core versions"""
    try:
        return wg_portfolio_matrices_service.get_fhir_resource_ownership()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/wg-ballot-specs-matrix")
async def get_wg_ballot_specs_matrix():
    """Specifications balloted by work group over HL7 trimesters"""
    try:
        return wg_portfolio_matrices_service.get_ballot_specs()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/workgroup-status")
async def get_workgroup_status():
    """Sunset/deprecated work groups from Jira _workgroups.xml"""
    try:
        return wg_portfolio_matrices_service.get_workgroup_status()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/summary")
async def get_wg_meeting_participation_summary():
    """Portfolio KPIs + per-WG meeting participation rollup"""
    try:
        return wg_meeting_participation_service.get_summary()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/trimesters")
async def get_wg_meeting_participation_trimesters():
    """WG × trimester meeting participation matrix"""
    try:
        return wg_meeting_participation_service.get_trimesters()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/meetings")
async def get_wg_meeting_participation_meetings(wg_key: Optional[str] = Query(None)):
    """Per-meeting drill-down (optionally filtered by wg_key)"""
    try:
        return wg_meeting_participation_service.get_meetings(wg_key)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/people")
async def get_wg_meeting_participation_people(wg_key: Optional[str] = Query(None)):
    """Person index from minutes attendance (optionally filtered by wg_key)"""
    try:
        return wg_meeting_participation_service.get_people(wg_key)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/organizations")
async def get_wg_meeting_participation_organizations(wg_key: Optional[str] = Query(None)):
    """Organization index from minutes attendance (optionally filtered by wg_key)"""
    try:
        return wg_meeting_participation_service.get_organizations(wg_key)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wg-meeting-participation/workgroups/{wg_key}")
async def get_wg_meeting_participation_workgroup(wg_key: str):
    """One work group: summary row + meetings + people + orgs"""
    try:
        return wg_meeting_participation_service.get_workgroup(wg_key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/meeting-locations")
async def get_standards_development_meeting_locations():
    """WGM host country by T{N} period, from the New Attendees CSV"""
    try:
        return meeting_locations_service.get_locations_payload()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/llm-prompt/{scope}/download")
async def download_standards_development_llm_prompt(scope: str):
    """Download the zip written by the most recent prompt for this page."""
    if scope not in ("cards", "insights"):
        raise HTTPException(status_code=404, detail="Prompt package not found")
    package_file = Path(f"data/processed/standards_development_llm_prompt_{scope}.zip")
    if not package_file.is_file():
        raise HTTPException(status_code=404, detail="Generate a prompt before downloading")
    return FileResponse(
        package_file,
        media_type="application/zip",
        filename=package_file.name,
    )

@app.post("/api/standards-development/llm-prompt")
async def generate_standards_development_llm_prompt(body: StandardsDevelopmentPromptRequest):
    """Build a paste-ready prompt from the Standards Development page data and the shared context file."""
    try:
        return standards_development_prompt_service.generate(
            scope=body.scope,
            question=body.question,
            kpi_only=body.kpi_only,
            include_publications=body.include_publications,
            charts=body.charts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/indicators/{tag}", response_model=List[KPIIndicator])
async def get_standards_development_indicators(tag: str):
    """Get indicators for Standards Development filtered by tag (case insensitive)"""
    try:
        # Use case-insensitive steward matching
        steward = "Standards Development"
        return data_service.get_standards_development_indicators(steward=steward, tag=tag)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# HL7 Family Colors for composite package version charts (R4, R4B, R5)
PACKAGE_VERSIONS_COLORS = ["#ea7125", "#5f9baf", "#0f8e48"]  # orange, blue, green

@app.get("/api/standards-development/charts/package-versions-new", response_model=FinancialChartData)
async def get_package_versions_new_chart():
    """Get composite chart for Package versions: New R4, R4B, R5"""
    try:
        return data_service.get_composite_package_versions_chart(
            chart_type="new",
            indicator_ids=["49", "50", "51"],
            colors=PACKAGE_VERSIONS_COLORS,
            labels=["R4", "R4B", "R5"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/charts/package-versions-total", response_model=FinancialChartData)
async def get_package_versions_total_chart():
    """Get composite chart for Package versions: Total R4, R4B, R5"""
    try:
        return data_service.get_composite_package_versions_chart(
            chart_type="total",
            indicator_ids=["52", "53", "54"],
            colors=PACKAGE_VERSIONS_COLORS,
            labels=["R4", "R4B", "R5"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/standards-development/charts/{indicator_id}", response_model=FinancialChartData)
async def get_standards_development_indicator_chart(indicator_id: str):
    """Get chart data for a specific Standards Development indicator"""
    try:
        indicator = data_service.get_indicator_by_id(indicator_id)
        if not indicator:
            raise HTTPException(status_code=404, detail="Indicator not found")
        return data_service.get_indicator_chart_data(indicator)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Published Standards Endpoints
@app.get("/api/published-standards/years")
async def get_published_standards_years():
    """Get list of available years for published standards"""
    try:
        years = published_standards_service.get_available_years()
        return {"years": years}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/published-standards/year/{year}")
async def get_published_standards_for_year(year: int):
    """Get all published standards for a specific year"""
    try:
        standards = published_standards_service.get_standards_for_year(year)
        return {
            "year": year,
            "standards": standards,
            "count": len(standards)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/published-standards/chart", response_model=FinancialChartData)
async def get_published_standards_chart():
    """Get chart data for published specifications indicators (27, 47, 48)"""
    try:
        # Get indicators 27, 47, 48
        indicator_27 = data_service.get_indicator_by_id("27")  # Total published specifications
        indicator_47 = data_service.get_indicator_by_id("47")  # U.S. Realm
        indicator_48 = data_service.get_indicator_by_id("48")  # Universal Realm
        
        if not indicator_27:
            raise HTTPException(status_code=404, detail="Indicator 27 not found")
        
        # Trimester periods only (exclude AllTime / other non-chart labels)
        trimester_re = re.compile(r'^\d{4}-T[1-3]$')
        periods = sorted(
            p for p in indicator_27.measurements.keys()
            if trimester_re.match(p)
            and indicator_27.measurements[p].value is not None
        )
        
        # Extract data for each indicator
        labels = []
        total_values = []  # Indicator 27
        us_realm_values = []  # Indicator 47
        universal_realm_values = []  # Indicator 48
        
        for period in periods:
            labels.append(period)
            
            # Get total (indicator 27)
            total_measurement = indicator_27.measurements.get(period)
            total_values.append(total_measurement.value if total_measurement and total_measurement.value is not None else 0)
            
            # Get U.S. Realm (indicator 47)
            if indicator_47:
                us_measurement = indicator_47.measurements.get(period)
                us_realm_values.append(us_measurement.value if us_measurement and us_measurement.value is not None else 0)
            else:
                us_realm_values.append(0)
            
            # Get Universal Realm (indicator 48)
            if indicator_48:
                universal_measurement = indicator_48.measurements.get(period)
                universal_realm_values.append(universal_measurement.value if universal_measurement and universal_measurement.value is not None else 0)
            else:
                universal_realm_values.append(0)
        
        # Create datasets for stacked area chart
        # U.S. Realm (blue-dk) stacks on bottom, Universal Realm (green) stacks on top
        # Together they should equal the total (red line)
        datasets = [
            {
                "label": "U.S. Realm",
                "data": us_realm_values,
                "backgroundColor": "rgba(0, 17, 64, 0.7)",  # HL7 blue-dk (#001140) with transparency
                "borderColor": "#001140",  # HL7 blue-dk
                "borderWidth": 1,
                "fill": True,
                "tension": 0.4,
                "pointRadius": 3,
                "pointHoverRadius": 5,
                "order": 2  # Draw first (bottom layer)
            },
            {
                "label": "Universal Realm",
                "data": universal_realm_values,
                "backgroundColor": "rgba(15, 142, 72, 0.7)",  # HL7 green (#0f8e48) with transparency
                "borderColor": "#0f8e48",  # HL7 green
                "borderWidth": 1,
                "fill": True,
                "tension": 0.4,
                "pointRadius": 3,
                "pointHoverRadius": 5,
                "order": 1  # Draw second (middle layer, stacks on top of U.S. Realm)
            },
            {
                "label": "Total Published Specifications",
                "data": total_values,
                "borderColor": "#dc2626",  # HL7 red
                "backgroundColor": "transparent",
                "borderWidth": 3,
                "fill": False,
                "tension": 0.4,
                "pointRadius": 5,
                "pointHoverRadius": 7,
                "order": 0  # Draw last (on top)
            }
        ]
        
        return FinancialChartData(
            labels=labels,
            datasets=datasets,
            type="line",
            title="Published Specifications by Realm",
            description="Total published specifications (red line) with U.S. Realm (blue) and Universal Realm (green) proportions"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/membership/charts/member-retention", response_model=FinancialChartData)
async def get_member_retention_chart():
    """Get member retention rate chart data"""
    try:
        return data_service.get_member_retention_chart_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{steward}", response_class=HTMLResponse)
async def steward_dashboard(request: Request, steward: str):
    """Dynamic dashboard page for any steward"""
    try:
        # Get all available stewards to validate
        metadata = data_service.get_metadata()
        if not metadata or steward not in metadata.stewards:
            raise HTTPException(status_code=404, detail="Steward not found")
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "webawesome_key": WEBAWESOME_KEY,
                "steward": steward
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/refresh/dry-run")
async def refresh_data_dry_run():
    """Dry run to preview what would be updated for indicators 27, 28, 47, 48
    Includes QA comparison of existing vs calculated values for indicators 27 and 28
    """
    try:
        from data.csv_to_json_converter import CSVToJSONConverter
        
        converter = CSVToJSONConverter()
        result = converter.populate_indicators(dry_run=True)
        
        qa_comparisons = result.get("qa_comparisons", [])
        qa_summary = result.get("summary", {}).get("qa_comparisons", {})
        
        return {
            "status": "success",
            "message": "Dry run completed - no data was modified",
            "dry_run": True,
            "updates": result.get("updates", []),
            "summary": result.get("summary", {}),
            "total_periods": result.get("total_periods_updated", 0),
            "qa_comparison": {
                "total_comparisons": qa_summary.get("total_comparisons", 0),
                "matches": qa_summary.get("matches", 0),
                "mismatches": qa_summary.get("mismatches", 0),
                "comparisons": qa_summary.get("comparisons", []),
                "all_match": qa_summary.get("mismatches", 0) == 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in dry run: {str(e)}")

@app.post("/api/refresh")
async def refresh_data():
    """Refresh data by processing raw CSV files and updating the JSON"""
    try:
        # Import the CSV converter
        from data.csv_to_json_converter import CSVToJSONConverter
        
        # Process raw CSV files and update the JSON
        converter = CSVToJSONConverter()
        
        # First populate indicators 27, 28, 47, 48 from published standards CSV
        populate_result = converter.populate_indicators(dry_run=False)
        
        # Then convert the updated CSV to JSON
        output_path = converter.save_json(populate_indicators=False)
        
        # Reload the data service with the updated JSON
        data_service.reload_data()

        # Clear published-standards CSV cache so year lists pick up file replacements
        published_standards_service.refresh_data()
        meeting_locations_service.refresh_data()
        
        return {
            "status": "success", 
            "message": "Data refreshed successfully from raw CSV files",
            "output_path": output_path,
            "indicators_populated": {
                "total_updates": populate_result.get("total_periods_updated", 0),
                "summary": populate_result.get("summary", {})
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Dashboard API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 