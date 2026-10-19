# Data Parsing Guide

This guide explains how to parse and refresh the underlying financial data sources.

## Overview

The consolidated financial data model pulls from three sources:
1. **IRS Form 990 Filings** - Parsed from XML files
2. **Audited Financial Statements** - Parsed from PDF files
3. **Budget Data** - Manually entered or imported

## How Data Flows

```
Source Files → Parsers → Individual Cache Files → Consolidated Data
```

1. **Source Files**: Raw data (XML, PDF, or manual entry)
2. **Parsers**: Extract structured data from source files
3. **Individual Cache Files**: Store parsed data separately
   - `data/processed/financial_data.json` (990 data)
   - `data/processed/audited_financial_data.json` (audited data)
4. **Consolidated Data**: Merged view in `data/processed/consolidated_financial_data.json`

## Parsing 990 Filings

### Source Files
- Location: `data/990s/`
- Format: XML files (e.g., `990_2023.xml`)

### How to Parse
1. **Via API**:
   ```bash
   curl -X POST http://localhost:8000/api/financial/refresh
   ```

2. **Via Python**:
   ```python
   from app.financial_service import FinancialDataService
   
   service = FinancialDataService()
   service.refresh_financial_data()
   ```

3. **Automatic**: Parsing happens automatically when:
   - The cache file doesn't exist
   - The service is first initialized

### What Gets Parsed
- Revenue breakdown (program services, contributions, investment income)
- Expense breakdown (salaries, other expenses, detailed categories)
- Balance sheet data (assets, liabilities, net assets)
- Employee and volunteer counts

## Parsing Audited Financial Statements

### Source Files
- Location: `data/audited-financials/`
- Format: PDF files (e.g., `HL7 2023 and 2024 Audited Financial Statements.pdf`)

### How to Parse
1. **Via API**:
   ```bash
   curl -X POST http://localhost:8000/api/audited-financial/refresh
   ```
   This will:
   - Parse all PDFs in `data/audited-financials/`
   - Update `data/processed/audited_financial_data.json`
   - Refresh the consolidated data file

2. **Via Python**:
   ```python
   from app.audited_financials_service import AuditedFinancialsService
   
   service = AuditedFinancialsService()
   service.refresh_financial_data()
   ```

3. **Automatic**: Parsing happens automatically when:
   - The cache file doesn't exist
   - The service is first initialized

### What Gets Parsed
- Statement of Financial Position (Balance Sheet)
- Statement of Activities (Income Statement)
- Statement of Functional Expenses (with Program/Supporting breakdown)

### Handling Multiple Years
- Most PDFs contain 2 years of data (current and prior year)
- The parser automatically extracts both years
- Duplicate years are deduplicated (prefers more complete data)

## Refreshing Consolidated Data

The consolidated data file is automatically updated when:
1. You refresh individual sources (990 or audited)
2. You call the consolidated refresh endpoint

### Via API
```bash
curl -X POST http://localhost:8000/api/consolidated-financial/refresh
```

### Via Python
```python
from app.consolidated_financial_service import ConsolidatedFinancialService

service = ConsolidatedFinancialService()
service.refresh_consolidated_data()
```

## Adding Budget Data

Budget data is not automatically parsed - it must be manually added.

### Via API
```python
from app.consolidated_financial_service import ConsolidatedFinancialService
from app.models import BudgetData

service = ConsolidatedFinancialService()

budget = BudgetData(
    year=2024,
    version="final",
    total_revenue=12000000.0,
    total_expenses=11500000.0,
    program_service_revenue=8500000.0,
    contributions_grants=2000000.0,
    investment_income=500000.0,
    other_revenue=1000000.0,
    salaries_compensation=6000000.0,
    other_expenses=5500000.0,
    # ... other fields
)

service.add_budget_data(2024, budget, is_final=True)
```

### Via JSON File
Edit `data/processed/consolidated_financial_data.json` directly:

```json
{
  "years": [
    {
      "year": 2024,
      "budget_final": {
        "year": 2024,
        "version": "final",
        "total_revenue": 12000000.0,
        "total_expenses": 11500000.0,
        ...
      }
    }
  ]
}
```

Then refresh the consolidated data to recalculate variances.

## Data Refresh Workflow

### Complete Refresh (All Sources)
```bash
# 1. Refresh 990 data
curl -X POST http://localhost:8000/api/financial/refresh

# 2. Refresh audited data
curl -X POST http://localhost:8000/api/audited-financial/refresh

# 3. Refresh consolidated data (picks up both)
curl -X POST http://localhost:8000/api/consolidated-financial/refresh
```

### Individual Source Refresh
- **990 only**: `POST /api/financial/refresh`
- **Audited only**: `POST /api/audited-financial/refresh` (also updates consolidated)
- **Consolidated only**: `POST /api/consolidated-financial/refresh` (rebuilds from existing sources)

## Troubleshooting

### Data Not Appearing
1. Check that source files exist in the correct directories
2. Check for parsing errors in the console/logs
3. Verify cache files are being created/updated
4. Try manually refreshing the consolidated data

### Incorrect Data
1. Check the source files (XML/PDF) for accuracy
2. Review parsing validation warnings
3. Check for duplicate year entries
4. Verify field mappings in the models

### Missing Years
1. Ensure source files are named correctly
2. Check that years are being extracted from filenames/text
3. Verify PDFs contain the expected year data
4. Check for parsing errors for specific years

## File Locations

- **990 XML files**: `data/990s/`
- **Audited PDF files**: `data/audited-financials/`
- **990 cache**: `data/processed/financial_data.json`
- **Audited cache**: `data/processed/audited_financial_data.json`
- **Consolidated data**: `data/processed/consolidated_financial_data.json`





