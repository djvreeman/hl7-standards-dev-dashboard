#!/usr/bin/env python3
"""
Font Setup Script for HL7 Standards Development Dashboard

This script helps set up the font directory structure for the proprietary
Gotham font files that are excluded from version control.
"""

import os
import sys
from pathlib import Path

def create_font_directories():
    """Create the necessary font directories."""
    font_dir = Path("static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)")
    
    try:
        font_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created font directory: {font_dir}")
        return True
    except Exception as e:
        print(f"❌ Error creating font directory: {e}")
        return False

def check_font_files():
    """Check if required font files are present."""
    font_dir = Path("static/fonts/HCo_Gotham_Bundle/Fonts (OpenType)")
    
    required_fonts = [
        "Gotham-Thin.otf",
        "Gotham-ThinItalic.otf",
        "Gotham-XLight.otf",
        "Gotham-XLightItalic.otf",
        "Gotham-Light.otf",
        "Gotham-LightItalic.otf",
        "Gotham-Book.otf",
        "Gotham-BookItalic.otf",
        "Gotham-Medium.otf",
        "Gotham-MediumItalic.otf",
        "Gotham-Bold.otf",
        "Gotham-BoldItalic.otf",
        "Gotham-Black.otf",
        "Gotham-BlackItalic.otf",
        "Gotham-Ultra.otf",
        "Gotham-UltraItalic.otf"
    ]
    
    missing_fonts = []
    present_fonts = []
    
    for font in required_fonts:
        font_path = font_dir / font
        if font_path.exists():
            present_fonts.append(font)
        else:
            missing_fonts.append(font)
    
    print(f"\n📊 Font File Status:")
    print(f"   ✅ Present: {len(present_fonts)}/{len(required_fonts)}")
    print(f"   ❌ Missing: {len(missing_fonts)}/{len(required_fonts)}")
    
    if present_fonts:
        print(f"\n✅ Found font files:")
        for font in present_fonts:
            print(f"   - {font}")
    
    if missing_fonts:
        print(f"\n❌ Missing font files:")
        for font in missing_fonts:
            print(f"   - {font}")
        
        print(f"\n📋 To complete font setup:")
        print(f"   1. Copy your licensed Gotham font files to:")
        print(f"      {font_dir.absolute()}")
        print(f"   2. Ensure all {len(required_fonts)} font files are present")
        print(f"   3. Run this script again to verify")
    
    return len(missing_fonts) == 0

def main():
    """Main setup function."""
    print("🎨 HL7 Gotham Font Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("app").exists() or not Path("static").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Create directories
    if not create_font_directories():
        sys.exit(1)
    
    # Check font files
    fonts_complete = check_font_files()
    
    if fonts_complete:
        print(f"\n🎉 Font setup complete! All required fonts are present.")
        print(f"   The dashboard will now use the HL7 Gotham font family.")
    else:
        print(f"\n⚠️  Font setup incomplete. The dashboard will fall back to system fonts.")
        print(f"   See FONT_IMPLEMENTATION.md for detailed deployment instructions.")

if __name__ == "__main__":
    main() 