#!/usr/bin/env python3
"""
HL7 KPI Dashboard Runner Script

This script provides an easy way to start the dashboard application.
"""
import uvicorn
import os
from dotenv import load_dotenv

def main():
    """Start the FastAPI application"""
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"Starting HL7 KPI Dashboard...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Dashboard URL: http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

if __name__ == "__main__":
    main() 