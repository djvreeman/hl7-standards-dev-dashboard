# Indicator Card Image Feature

This feature allows KPI indicator cards to display images alongside their key values. This is particularly useful for showing geographic visualizations, trend charts, or other visual data representations.

## How It Works

1. **CSV Structure**: Add an `Image` column to your CSV file (`data/raw/all_kpis.csv`)
2. **Image Storage**: Place image files in the `data/raw/` directory
3. **Automatic Processing**: During CSV to JSON conversion, images are automatically copied to `static/indicators/`
4. **Display**: Images appear in indicator cards above the main value

## Usage

### Adding Images to Indicators

1. **Prepare your image file** (supports PNG, JPG, SVG, etc.)
2. **Place it in `data/raw/`** directory
3. **Add the filename to your CSV** in the `Image` column:

```csv
ID,Time Period,Domain,Indicator,Type,Unit,Value,Notes,Steward,Target,Target Type,Target Operation,Tags,Image
CSDO-20,2025-T1,Global Engagement,Active participants,N,count,95599,,CSDO,,,,,active_participants_map.svg
```

4. **Run the converter** to process the data:
   ```bash
   python data/csv_to_json_converter.py
   ```

5. **Refresh the dashboard** data:
   ```bash
   curl -X POST http://localhost:8000/api/refresh
   ```

### Image Requirements

- **Format**: Any web-compatible image format (PNG, JPG, SVG, GIF, etc.)
- **Size**: Recommended max width of 400px for optimal display
- **Location**: Must be placed in `data/raw/` directory
- **Naming**: Use descriptive filenames (e.g., `active_participants_map.svg`)

### Example Use Cases

1. **Geographic Visualizations**: World maps showing participant distribution
2. **Trend Charts**: Line charts showing historical data trends
3. **Process Diagrams**: Flowcharts for complex processes
4. **Infographics**: Visual representations of key metrics

## Technical Implementation

### Files Modified

1. **`app/models.py`**: Added `image` field to `KPIIndicator` model
2. **`data/csv_to_json_converter.py`**: Added image copying functionality
3. **`templates/dashboard.html`**: Added image display in KPI cards
4. **`data/raw/all_kpis.csv`**: Added `Image` column

### CSS Classes

- `.kpi-image-section`: Container for the image
- `.kpi-image`: Styling for the image itself
- Hover effects and responsive design included

### API Response

The KPI cards API now includes the image field:

```json
{
  "indicator": {
    "id": "CSDO-20",
    "name": "Active participants",
    "image": "active_participants_map.svg",
    ...
  }
}
```

## Future Enhancements

This feature is designed to be extensible for future enhancements:

1. **Trend Charts**: Dynamic chart generation based on measurement data
2. **Interactive Visualizations**: Clickable maps or charts
3. **Multiple Images**: Support for multiple images per indicator
4. **Image Galleries**: Carousel of related visualizations

## Troubleshooting

### Image Not Displaying

1. Check that the image file exists in `data/raw/`
2. Verify the filename in the CSV matches exactly
3. Ensure the converter ran successfully
4. Check browser console for 404 errors
5. Verify the image was copied to `static/indicators/`

### Image Copy Issues

1. Check file permissions on `data/raw/` and `static/indicators/`
2. Ensure the image file is not corrupted
3. Verify the converter has write permissions

### Performance

- Use optimized image formats (SVG for vector graphics, WebP for photos)
- Keep image sizes reasonable (under 500KB recommended)
- Consider lazy loading for large numbers of images 