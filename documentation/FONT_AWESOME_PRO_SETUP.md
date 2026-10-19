# Font Awesome Pro Setup Guide

## To Enable Font Awesome Pro Icons

If you have a Font Awesome Pro license, you need to configure it in your `.env` file:

1. **Get your Font Awesome Kit Token:**
   - Go to https://fontawesome.com/kits
   - Find your kit or create a new one
   - Copy your Kit Token (it looks like: `abc123def456`)

2. **Add to `.env` file:**
   ```env
   WEBAWESOME_KEY=your_font_awesome_kit_token_here
   ```

3. **Restart the application:**
   ```bash
   # If running locally
   python run.py
   
   # If running as a service
   sudo systemctl restart hl7-standards-dev-dashboard
   ```

## Alternative: Direct Font Awesome Pro CDN

If WebAwesome doesn't work with your Pro license, you can also add Font Awesome Pro directly to the template:

1. Get your Font Awesome Kit URL from https://fontawesome.com/kits
2. Add this to the template `<head>` section:
   ```html
   <script src="https://kit.fontawesome.com/YOUR_KIT_TOKEN.js" crossorigin="anonymous"></script>
   ```

## Icon Usage

The icons are used with Font Awesome classes:
- Globe: `<i class="fas fa-globe"></i>`
- US Flag: `<i class="fas fa-flag-usa"></i>`
- Rocket: `<i class="fas fa-rocket"></i>`

Make sure your Font Awesome Pro license includes these icons.
