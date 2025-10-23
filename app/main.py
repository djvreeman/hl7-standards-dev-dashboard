from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv

from app.models import KPICard, KPISummary, KPIFilter, ChartData, DashboardMetrics, KPIIndicator, FinancialHealthMetrics, FinancialChartData
from app.data_service import DataService
from app.financial_service import FinancialDataService

# Load environment variables
load_dotenv()

app = FastAPI(
    title="HL7 KPI Dashboard",
    description="Company dashboard for displaying KPIs and key metrics",
    version="1.0.0"
)

# Initialize data services
data_service = DataService()
financial_service = FinancialDataService()

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

# Financial Health Dashboard Endpoints
@app.get("/financial-health", response_class=HTMLResponse)
async def financial_health_dashboard(request: Request):
    """Financial health dashboard page"""
    return templates.TemplateResponse(
        "finance_dashboard.html",
        {
            "request": request,
            "webawesome_key": WEBAWESOME_KEY
        }
    )

@app.get("/api/financial/health", response_model=FinancialHealthMetrics)
async def get_financial_health():
    """Get financial health metrics"""
    try:
        return financial_service.get_financial_health_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/summary")
async def get_financial_summary():
    """Get financial summary statistics"""
    try:
        return financial_service.get_financial_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/financial/charts/{chart_type}", response_model=FinancialChartData)
async def get_financial_chart(chart_type: str):
    """Get financial chart data"""
    try:
        if chart_type == "revenue-expense-trend":
            return financial_service.get_revenue_expense_trend_chart()
        elif chart_type == "revenue-composition":
            return financial_service.get_revenue_composition_chart()
        elif chart_type == "key-revenue-streams":
            return financial_service.get_key_revenue_streams_chart()
        elif chart_type == "expense-breakdown":
            return financial_service.get_expense_breakdown_chart()
        elif chart_type == "program-service-breakdown":
            return financial_service.get_program_service_breakdown_chart()
        elif chart_type == "detailed-expense-trends":
            return financial_service.get_detailed_expense_trends_chart()
        else:
            raise HTTPException(status_code=404, detail="Chart type not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/financial/refresh")
async def refresh_financial_data():
    """Refresh financial data by re-parsing 990 XML files"""
    try:
        financial_service.refresh_financial_data()
        return {
            "status": "success",
            "message": "Financial data refreshed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing financial data: {str(e)}")

@app.get("/api/financial/llm-prompt")
async def generate_llm_prompt():
    """Generate LLM prompt for financial analysis"""
    try:
        prompt = financial_service.generate_llm_prompt()
        return {
            "status": "success",
            "message": "LLM prompt generated successfully",
            "prompt_file": "data/processed/llm_prompt.txt"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM prompt: {str(e)}")

@app.get("/api/financial/insights")
async def get_financial_insights():
    """Get financial insights from markdown file and convert to HTML"""
    try:
        insights_file = Path("data/processed/financial_insights.md")
        if insights_file.exists():
            with open(insights_file, 'r') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = financial_service.parse_markdown_to_html(markdown_content)
            return {"insights": html_content, "format": "html"}
        else:
            return {"insights": "No insights file found. Please generate LLM prompt and create insights markdown file.", "format": "text"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading insights: {str(e)}")

@app.get("/api/financial/detailed-table")
async def get_detailed_financial_table():
    """Get detailed financial data table (2019-2024)"""
    try:
        table_data = financial_service.get_detailed_financial_table()
        return table_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading detailed table: {str(e)}")

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

@app.post("/api/refresh")
async def refresh_data():
    """Refresh data by processing raw CSV files and updating the JSON"""
    try:
        # Import the CSV converter
        from data.csv_to_json_converter import CSVToJSONConverter
        
        # Process raw CSV files and update the JSON
        converter = CSVToJSONConverter()
        output_path = converter.save_json()
        
        # Reload the data service with the updated JSON
        data_service.reload_data()
        
        return {
            "status": "success", 
            "message": "Data refreshed successfully from raw CSV files",
            "output_path": output_path
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