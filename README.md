# HL7 KPI Dashboard

A comprehensive company dashboard for displaying KPIs and key metrics using FastAPI, Python, and WebAwesome framework.

## Features

- **Real-time KPI Visualization**: Interactive charts and graphs showing KPI trends
- **Advanced Filtering**: Filter KPIs by time period, domain, steward, and indicator name
- **Trend Analysis**: Automatic calculation and display of KPI trends between time periods
- **Alert System**: Intelligent alerts based on KPI thresholds and performance changes
- **Responsive Design**: Modern, mobile-friendly interface using WebAwesome framework
- **RESTful API**: Clean API endpoints for data access and integration
- **Secure Configuration**: Environment-based configuration management

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript with WebAwesome framework
- **Data Processing**: Pandas, NumPy
- **Charts**: Chart.js
- **Styling**: WebAwesome CSS framework
- **Configuration**: Python-dotenv

## Project Structure

```
hl7-standards-dev-dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic data models
│   └── data_service.py      # Data processing service
├── data/
│   └── kpis/
│       ├── raw/
│       │   ├── all_kpis.csv              # KPI data source
│       │   └── indicator-definitions.csv # KPI definitions
│       └── processed/                    # Processed data files
├── static/
│   ├── css/
│   │   ├── dashboard.css    # Additional styles
│   │   └── fonts.css        # HL7 Gotham font declarations
│   └── fonts/               # Font files (excluded from git)
│       └── HCo_Gotham_Bundle/
│           └── Fonts (OpenType)/  # Proprietary font files
├── templates/
│   └── dashboard.html       # Main dashboard template
├── requirements.txt         # Python dependencies
├── env.example             # Environment configuration template
└── README.md
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd hl7-standards-dev-dashboard
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env file with your configuration
   ```

5. **Configure WebAwesome License**:
   - Get your WebAwesome license key from [https://webawesome.com/](https://webawesome.com/)
   - Add it to your `.env` file:
     ```
     WEBAWESOME_KEY=your_license_key_here
     ```

6. **Set up HL7 Brand Fonts (Optional)**:
   ```bash
   python setup_fonts.py
   ```
   - This will create the necessary font directories
   - Copy your licensed Gotham font files to `static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)/`
   - See `FONT_IMPLEMENTATION.md` for detailed instructions

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# WebAwesome License Key (Required for advanced features)
WEBAWESOME_KEY=your_webawesome_license_key_here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1

# Logging
LOG_LEVEL=INFO
```

### Data Source

The dashboard reads KPI data from `data/kpis/raw/all_kpis.csv`. Ensure this file exists and contains the following columns:

- `ID`: Unique identifier for each KPI
- `Time Period`: Reporting period (e.g., "2024-T3", "2025-T1")
- `Domain`: KPI category/domain
- `Indicator`: KPI name/description
- `Type`: Measurement type (N, %, etc.)
- `Value`: KPI value
- `Notes`: Additional notes
- `Steward`: Organization responsible for the KPI
- `Target`: Target value (optional)

## Usage

### Running the Application

1. **Start the development server**:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the dashboard**:
   - Open your browser and navigate to `http://localhost:8000`
   - The dashboard will load automatically with your KPI data

### Updating Processed Data

Whenever you add or update data in the raw CSV files (`data/raw/all_kpis.csv` and `data/raw/indicator-definitions.csv`), you should regenerate the processed JSON file for the dashboard:

```bash
python update_data.py
```

This will read the latest CSVs and output an updated `data/processed/kpi_data.json` file, which is used by the dashboard and API. Make sure to run this command before starting the server if you have changed the data.

> **Note:** To start the dashboard server, use `python run.py`.

### API Endpoints

The application provides the following REST API endpoints:

- `GET /`: Main dashboard page
- `GET /api/kpis`: Get all KPIs with optional filtering
- `GET /api/kpis/summary`: Get KPI summary statistics
- `GET /api/kpis/trends`: Get KPI trends between time periods
- `GET /api/charts/{chart_type}`: Get chart data for visualizations
- `GET /api/alerts`: Get KPI alerts and notifications
- `GET /api/dashboard`: Get complete dashboard data
- `GET /health`: Health check endpoint

### API Query Parameters

Filter KPIs using query parameters:

```bash
# Filter by time period
GET /api/kpis?time_period=2025-T1

# Filter by domain
GET /api/kpis?domain=Standards Development

# Filter by steward
GET /api/kpis?steward=CSDO

# Search indicators
GET /api/kpis?indicator=membership
```

## Dashboard Features

### Summary Statistics
- Total number of indicators
- Distribution across domains
- Distribution across stewards
- Number of time periods

### Interactive Charts
- **Domain Distribution**: Pie chart showing KPI distribution by domain
- **Steward Distribution**: Bar chart showing KPI distribution by steward
- **Trend Analysis**: Line charts showing KPI trends over time

### Advanced Filtering
- Filter by time period
- Filter by domain
- Filter by steward
- Search by indicator name
- Real-time filtering with instant results

### Alert System
- Automatic trend detection
- Performance threshold alerts
- Color-coded severity levels
- Actionable insights

## Development

### Adding New Features

1. **New API Endpoints**: Add routes in `app/main.py`
2. **Data Models**: Extend models in `app/models.py`
3. **Data Processing**: Add methods in `app/data_service.py`
4. **Frontend**: Modify `templates/dashboard.html` and `static/css/dashboard.css`

### Testing

```bash
# Run the application in development mode
python -m uvicorn app.main:app --reload

# Test API endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/kpis
```

### Deployment

For production deployment:

1. **Set production environment variables**:
   ```env
   DEBUG=False
   SECRET_KEY=your_secure_secret_key
   ```

2. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Set up reverse proxy** (nginx example):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Security Considerations

- Store sensitive configuration in environment variables
- Use HTTPS in production
- Implement proper authentication for production use
- Validate and sanitize all user inputs
- Keep dependencies updated

## Future Enhancements

- **Database Integration**: Replace CSV with PostgreSQL/MySQL
- **Tableau Integration**: Connect to Tableau for advanced analytics
- **Real-time Updates**: WebSocket support for live data updates
- **User Authentication**: Role-based access control
- **Export Features**: PDF/Excel export capabilities
- **Mobile App**: Native mobile application
- **Advanced Analytics**: Machine learning insights

## Troubleshooting

### Common Issues

1. **CSV file not found**:
   - Ensure `data/kpis/all_kpis.csv` exists
   - Check file permissions

2. **WebAwesome features not working**:
   - Verify your license key in `.env`
   - Check browser console for errors

3. **Charts not displaying**:
   - Ensure Chart.js is loading properly
   - Check for JavaScript errors in browser console

4. **API errors**:
   - Check server logs for detailed error messages
   - Verify CSV data format

### Logs

Check application logs for debugging:

```bash
# View real-time logs
tail -f logs/app.log

# Check for errors
grep ERROR logs/app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**Note**: This dashboard is designed for HL7 International and CSDO KPI data. Modify the data models and processing logic as needed for your specific use case.
