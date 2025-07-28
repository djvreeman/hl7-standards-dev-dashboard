# HL7 Gotham Font Implementation

This document describes the implementation of the HL7 brand font (Gotham) as the default sans-serif font for the HL7 Standards Development Dashboard.

## Overview

The Gotham font family has been implemented as the primary font for the dashboard, replacing the previous Inter font. Since Gotham is a commercially licensed font that's not generally available on most devices, it's served directly from the application server.

## Implementation Details

### Font Files
- **Location**: `static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)/`
- **Format**: OpenType (.otf)
- **Weights Available**:
  - Thin (100)
  - XLight (200)
  - Light (300)
  - Book (400) - Default
  - Medium (500)
  - Bold (700)
  - Black (900)
  - Ultra (950)
- **Styles**: Normal and Italic for each weight

### CSS Implementation

#### Font Declarations (`static/css/fonts.css`)
- Complete `@font-face` declarations for all Gotham weights and styles
- URL encoding for folder names with spaces (`Fonts%20(OpenType)`)
- `font-display: swap` for optimal loading performance
- CSS custom properties for font family variables

#### Font Variables
```css
:root {
    --font-family-primary: 'Gotham', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-family-secondary: 'Gotham', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-family-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
}
```

#### Typography Utilities
- Font weight classes: `.font-thin`, `.font-light`, `.font-normal`, `.font-medium`, `.font-bold`, `.font-black`, `.font-ultra`
- Font style classes: `.italic`, `.not-italic`
- Typography scale: `.text-xs` through `.text-5xl`

### Integration

#### HTML Template (`templates/dashboard.html`)
- Font CSS loaded before custom styles
- Body font-family set to use `var(--font-family-primary)`
- All text elements inherit the Gotham font family

#### Dashboard CSS (`static/css/dashboard.css`)
- Font family variable added to root CSS variables
- Specific elements explicitly set to use the primary font family
- Maintains existing design while applying Gotham consistently

### Server Configuration

The FastAPI application is configured to serve static files:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

This allows the font files to be served directly from the `static/fonts/` directory.

## Testing

### Font Test Page
A test page is available at `test_fonts.html` that demonstrates:
- All font weights and styles
- Typography scale
- Fallback behavior

### Test Server
Run the test server to verify font loading:
```bash
python test_font_server.py
```
Then visit `http://localhost:8080/test_fonts.html`

### Browser Developer Tools
To verify font loading:
1. Open browser developer tools
2. Go to Network tab
3. Reload the page
4. Look for `.otf` files being loaded
5. Check the Fonts tab to see if Gotham is loaded

## Performance Considerations

### Font Loading Strategy
- `font-display: swap` ensures text remains visible during font loading
- Fonts are served from the same domain (no CORS issues)
- Fallback fonts provide immediate text rendering

### File Size
- Total font bundle size: ~1.7MB
- Individual font files range from 105KB to 117KB
- Consider implementing font subsetting for production if needed

## Browser Support

The implementation supports:
- Modern browsers with OpenType font support
- Graceful fallback to system fonts for older browsers
- Progressive enhancement approach

## Maintenance

### Adding New Font Weights
1. Add the font file to the appropriate directory
2. Add `@font-face` declaration in `fonts.css`
3. Update CSS variables if needed
4. Test across browsers

### Updating Font Files
1. Replace font files in the bundle directory
2. Clear browser cache
3. Test font loading and rendering

## License Compliance

- Gotham font files are commercially licensed
- Implementation respects the license terms
- Fonts are served only from the authorized application
- No redistribution of font files outside the application
- Font files are excluded from version control (see `.gitignore`)

## Deployment Instructions

### Font Files Management

Since Gotham is a proprietary font, the font files are excluded from the Git repository. Follow these steps to deploy the application with fonts:

#### 1. Local Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd hl7-standards-dev-dashboard

# Create the fonts directory structure
mkdir -p static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/

# Copy your licensed Gotham font files to:
# static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)/
# 
# Required files:
# - Gotham-Thin.otf
# - Gotham-ThinItalic.otf
# - Gotham-XLight.otf
# - Gotham-XLightItalic.otf
# - Gotham-Light.otf
# - Gotham-LightItalic.otf
# - Gotham-Book.otf
# - Gotham-BookItalic.otf
# - Gotham-Medium.otf
# - Gotham-MediumItalic.otf
# - Gotham-Bold.otf
# - Gotham-BoldItalic.otf
# - Gotham-Black.otf
# - Gotham-BlackItalic.otf
# - Gotham-Ultra.otf
# - Gotham-UltraItalic.otf
```

#### 2. Production Deployment

**Option A: Direct File Transfer**
```bash
# On your production server
cd /path/to/your/app
mkdir -p static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/

# Transfer font files securely (e.g., via SCP, SFTP, or secure file upload)
scp -r /path/to/local/fonts/* user@server:/path/to/your/app/static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/
```

**Option B: Docker Deployment**
```dockerfile
# In your Dockerfile
FROM python:3.11-slim

# ... other setup steps ...

# Create fonts directory
RUN mkdir -p /app/static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/

# Copy application files
COPY . /app/

# Copy font files (ensure you have the font files in your build context)
COPY fonts/* /app/static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/

# ... rest of Dockerfile ...
```

**Option C: Cloud Deployment (AWS, GCP, Azure)**
```bash
# For cloud deployments, upload font files to your server via:
# - AWS S3 + CloudFront
# - Google Cloud Storage
# - Azure Blob Storage
# - Direct server upload via SSH/SCP

# Example for AWS S3:
aws s3 cp fonts/ s3://your-bucket/static/fonts/HCo_Gotham_Bundle/Fonts\ \(OpenType\)/ --recursive
```

#### 3. Verification Steps

After deployment, verify font loading:

1. **Check file accessibility**:
   ```bash
   curl -I "https://your-domain.com/static/fonts/HCo_Gotham_Bundle/Fonts%20(OpenType)/Gotham-Book.otf"
   ```

2. **Browser developer tools**:
   - Network tab: Look for `.otf` files loading
   - Fonts tab: Verify "Gotham" is listed as loaded
   - Console: No 404 errors for font files

3. **Visual verification**:
   - Text should render in Gotham font
   - Different font weights should be visible
   - No fallback to system fonts

#### 4. Security Considerations

- **File permissions**: Ensure font files are readable by the web server but not publicly accessible via direct URL manipulation
- **Access control**: Consider implementing additional access controls if needed
- **CDN**: Use a CDN for better performance while maintaining security
- **HTTPS**: Always serve fonts over HTTPS in production

#### 5. Fallback Strategy

If font files are missing or fail to load:
- The application will gracefully fall back to system fonts
- No functionality will be broken
- Users will still see properly formatted text
- Consider implementing font loading detection and user notification

## Troubleshooting

### Font Not Loading
1. Check file paths in CSS (URL encoding for spaces)
2. Verify static file serving is working
3. Check browser console for 404 errors
4. Ensure font files are accessible via HTTP

### Font Not Displaying
1. Check if font-family is properly applied
2. Verify CSS specificity
3. Test with browser developer tools
4. Check for CSS conflicts

### Performance Issues
1. Consider font subsetting
2. Implement font preloading
3. Use font-display: optional for non-critical fonts
4. Monitor font loading times 