#!/usr/bin/env python3
"""
Test script to verify target handling for period vs annual targets
"""

import json
from pathlib import Path

def test_target_handling():
    """Test that targets are handled correctly"""
    
    # Load the processed JSON data
    json_path = Path("data/processed/kpi_data.json")
    if not json_path.exists():
        print("❌ JSON file not found")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    print("🔍 Testing Target Handling")
    print("=" * 50)
    
    # Test CSDO-2 (period target)
    csdo2 = data['indicators']['CSDO-2']
    print(f"\n📊 CSDO-2: {csdo2['name']}")
    print(f"   Type: Period target")
    print(f"   Targets dict: {csdo2['targets']}")
    print(f"   Legacy target: {csdo2['target']}")
    print(f"   Measurements:")
    for period, measurement in csdo2['measurements'].items():
        print(f"     {period}: value={measurement['value']}, target={measurement['target']}")
    
    # Test CSDO-14 (annual target)
    csdo14 = data['indicators']['CSDO-14']
    print(f"\n📊 CSDO-14: {csdo14['name']}")
    print(f"   Type: Annual target")
    print(f"   Targets dict: {csdo14['targets']}")
    print(f"   Legacy target: {csdo14['target']}")
    print(f"   Measurements:")
    for period, measurement in csdo14['measurements'].items():
        print(f"     {period}: value={measurement['value']}, target={measurement['target']}")
    
    # Test CSDO-4 (no target)
    csdo4 = data['indicators']['CSDO-4']
    print(f"\n📊 CSDO-4: {csdo4['name']}")
    print(f"   Type: No target")
    print(f"   Targets dict: {csdo4['targets']}")
    print(f"   Legacy target: {csdo4['target']}")
    print(f"   Measurements:")
    for period, measurement in csdo4['measurements'].items():
        print(f"     {period}: value={measurement['value']}, target={measurement['target']}")
    
    print("\n✅ Target handling test completed!")

if __name__ == "__main__":
    test_target_handling() 