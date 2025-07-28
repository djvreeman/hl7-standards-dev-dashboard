from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from typing import List, Optional
import os
from dotenv import load_dotenv

from app.models import KPICard, KPISummary, KPIFilter, ChartData, DashboardMetrics, KPIIndicator
from app.data_service import DataService

# Load environment variables
load_dotenv()

app = FastAPI(
    title="HL7 KPI Dashboard",
    description="Company dashboard for displaying KPIs and key metrics",
    version="1.0.0"
)

# Initialize data service
data_service = DataService()

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