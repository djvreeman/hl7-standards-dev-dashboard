# Deployment Checklist

This checklist ensures all components are properly configured when deploying the HL7 Standards Development Dashboard.

## Pre-Deployment

### ✅ Environment Setup
- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured (`.env` file)
- [ ] WebAwesome license key added to `.env`

### ✅ Font Setup (Optional but Recommended)
- [ ] Run `python setup_fonts.py` to create font directories
- [ ] Copy licensed Gotham font files to `static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)/`
- [ ] Verify all 16 font files are present:
  - [ ] Gotham-Thin.otf
  - [ ] Gotham-ThinItalic.otf
  - [ ] Gotham-XLight.otf
  - [ ] Gotham-XLightItalic.otf
  - [ ] Gotham-Light.otf
  - [ ] Gotham-LightItalic.otf
  - [ ] Gotham-Book.otf
  - [ ] Gotham-BookItalic.otf
  - [ ] Gotham-Medium.otf
  - [ ] Gotham-MediumItalic.otf
  - [ ] Gotham-Bold.otf
  - [ ] Gotham-BoldItalic.otf
  - [ ] Gotham-Black.otf
  - [ ] Gotham-BlackItalic.otf
  - [ ] Gotham-Ultra.otf
  - [ ] Gotham-UltraItalic.otf

### ✅ Data Setup
- [ ] Raw CSV files present in `data/raw/`
  - [ ] `all_kpis.csv`
  - [ ] `indicator-definitions.csv`
- [ ] Processed data generated (`python update_data.py`)
- [ ] `data/processed/kpi_data.json` exists and is valid

## Deployment

### ✅ Server Configuration
- [ ] FastAPI application starts without errors
- [ ] Static files are accessible
- [ ] API endpoints respond correctly
- [ ] Dashboard loads in browser

### ✅ Font Verification
- [ ] Font CSS file loads (`/static/css/fonts.css`)
- [ ] Font files are accessible via HTTP
- [ ] Browser developer tools show fonts loading
- [ ] Text renders in Gotham font (not fallback fonts)

### ✅ Security
- [ ] HTTPS enabled in production
- [ ] Font files have appropriate permissions
- [ ] No sensitive data exposed
- [ ] Environment variables properly configured

## Post-Deployment

### ✅ Functionality Testing
- [ ] Dashboard loads completely
- [ ] All charts render correctly
- [ ] Filtering works as expected
- [ ] API endpoints return correct data
- [ ] Responsive design works on mobile

### ✅ Performance
- [ ] Page load time is acceptable
- [ ] Font files load efficiently
- [ ] No console errors
- [ ] Charts render smoothly

### ✅ Monitoring
- [ ] Health check endpoint responds (`/health`)
- [ ] Logs are being generated
- [ ] Error monitoring configured (if applicable)
- [ ] Performance monitoring set up (if applicable)

## Troubleshooting

### Font Issues
- **Fonts not loading**: Check file paths and permissions
- **Fallback fonts showing**: Verify font files are present and accessible
- **404 errors**: Ensure static file serving is configured correctly

### Data Issues
- **No data showing**: Run `python update_data.py` to regenerate processed data
- **Missing indicators**: Check raw CSV files for data completeness
- **API errors**: Verify data format and API endpoint configuration

### Server Issues
- **Port conflicts**: Change port in configuration or stop conflicting services
- **Permission errors**: Check file and directory permissions
- **Import errors**: Verify all dependencies are installed

## Quick Commands

```bash
# Check font setup
python setup_fonts.py

# Update processed data
python update_data.py

# Start development server
python run.py

# Check server health
curl http://localhost:8000/health

# Test font loading
curl -I "http://localhost:8000/static/fonts/HCo_Gotham_Bundle/Fonts%20(OpenType)/Gotham-Book.otf"
```

## Support

- **Font Implementation**: See `FONT_IMPLEMENTATION.md`
- **API Documentation**: Visit `/docs` when server is running
- **Configuration**: Check `env.example` for required environment variables 