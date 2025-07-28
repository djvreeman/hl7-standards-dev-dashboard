#!/usr/bin/env python3
"""
Test script to verify dashboard API target handling
"""

import requests
import json

def test_dashboard_api():
    """Test the dashboard API target handling"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Dashboard API Target Handling")
    print("=" * 50)
    
    try:
        # Test CSDO steward KPI cards
        response = requests.get(f"{base_url}/api/kpi-cards?steward=CSDO")
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            return
        
        kpi_cards = response.json()
        
        # Find specific indicators
        csdo2 = None
        csdo14 = None
        csdo4 = None
        
        for card in kpi_cards:
            if card['indicator']['id'] == 'CSDO-2':
                csdo2 = card
            elif card['indicator']['id'] == 'CSDO-14':
                csdo14 = card
            elif card['indicator']['id'] == 'CSDO-4':
                csdo4 = card
        
        # Test CSDO-2 (period target)
        if csdo2:
            print(f"\n📊 CSDO-2: {csdo2['indicator']['name']}")
            print(f"   Current Value: {csdo2['current_value']}")
            print(f"   Target Type: {csdo2['target_type']}")
            print(f"   Target Value: {csdo2['target_value']}")
            print(f"   Progress: {csdo2['progress_to_target']:.1f}%")
            print(f"   Expected: 21.0/20.0 = 105.0%")
        
        # Test CSDO-14 (annual target)
        if csdo14:
            print(f"\n📊 CSDO-14: {csdo14['indicator']['name']}")
            print(f"   Current Value: {csdo14['current_value']}")
            print(f"   Target Type: {csdo14['target_type']}")
            print(f"   Target Value: {csdo14['target_value']}")
            print(f"   Progress: {csdo14['progress_to_target']:.1f}%")
            print(f"   Expected: 13.0/30.0 = 43.3%")
        
        # Test CSDO-4 (no target)
        if csdo4:
            print(f"\n📊 CSDO-4: {csdo4['indicator']['name']}")
            print(f"   Current Value: {csdo4['current_value']}")
            print(f"   Target Type: {csdo4['target_type']}")
            print(f"   Target Value: {csdo4['target_value']}")
            print(f"   Progress: {csdo4['progress_to_target']}")
            print(f"   Expected: null (no target)")
        
        print("\n✅ Dashboard API test completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_dashboard_api() 