#!/usr/bin/env python3
"""
Test script to verify target operations for annual targets
"""

import requests
import json

def test_target_operations():
    """Test the different target operations for annual targets"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Target Operations for Annual Targets")
    print("=" * 60)
    
    try:
        # Test CSDO steward KPI cards
        response = requests.get(f"{base_url}/api/kpi-cards?steward=CSDO")
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            return
        
        kpi_cards = response.json()
        
        # Find annual target indicators
        annual_indicators = []
        for card in kpi_cards:
            if card['target_type'] == 'annual':
                annual_indicators.append(card)
        
        print(f"\n📊 Found {len(annual_indicators)} indicators with annual targets:")
        
        for card in annual_indicators:
            indicator = card['indicator']
            print(f"\n🎯 {indicator['id']}: {indicator['name']}")
            print(f"   Unit: {indicator['unit']}")
            print(f"   Target Operation: {indicator.get('target_operation', 'sum (default)')}")
            print(f"   Current Value: {card['current_value']}")
            print(f"   Target Value: {card['target_value']}")
            print(f"   Progress: {card['progress_to_target']:.1f}%")
            
            # Show the calculation logic
            if indicator.get('target_operation') == 'average':
                print(f"   Logic: Average of all {indicator['unit']} in current year")
            else:
                print(f"   Logic: Sum of all {indicator['unit']} in current year")
        
        # Test with mock data to show the difference
        print(f"\n🧮 Example Calculations:")
        print(f"   For CSDO-14 (Connectathon Tracks: Accelerator-led):")
        print(f"   - 2025-T1: 13 tracks")
        print(f"   - 2025-T2: 8 tracks (if available)")
        print(f"   - 2025-T3: 9 tracks (if available)")
        print(f"   - Sum: 13 + 8 + 9 = 30 tracks")
        print(f"   - Progress: 30/30 = 100%")
        
        print(f"\n   For a percentage metric with 'average' operation:")
        print(f"   - 2025-T1: 95%")
        print(f"   - 2025-T2: 98% (if available)")
        print(f"   - 2025-T3: 97% (if available)")
        print(f"   - Average: (95 + 98 + 97) / 3 = 96.7%")
        print(f"   - Progress: 96.7/90 = 107.4%")
        
        print("\n✅ Target operations test completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_target_operations() 