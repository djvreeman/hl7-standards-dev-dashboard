#!/usr/bin/env python3
"""
Update processed KPI data from raw CSV files.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from data.csv_to_json_converter import CSVToJSONConverter

def main():
    print("Updating processed KPI data from raw CSV files...")
    converter = CSVToJSONConverter()
    output_path = converter.save_json()
    print(f"\nDone! Processed data written to: {output_path}")

if __name__ == "__main__":
    main() 