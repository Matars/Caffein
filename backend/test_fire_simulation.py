#!/usr/bin/env python3
"""
Test script for the fire simulation API endpoint
"""

import requests
import json

# API endpoint
API_URL = "http://localhost:5001/api/simulate-fire"

# Test cases
test_cases = [
    {
        "name": "Stockholm Fire",
        "data": {
            "latitude": 59.33,
            "longitude": 18.07,
            "frp": 150,
            "pollutants": ["CO", "NO2", "AAI"]
        }
    },
    {
        "name": "Oslo Fire",
        "data": {
            "latitude": 59.91,
            "longitude": 10.75,
            "frp": 200,
            "pollutants": ["CO", "CH4", "SO2"]
        }
    },
    {
        "name": "Small Fire (Low FRP)",
        "data": {
            "latitude": 60.0,
            "longitude": 15.0,
            "frp": 50
        }
    },
    {
        "name": "Large Fire (High FRP)",
        "data": {
            "latitude": 65.0,
            "longitude": 20.0,
            "frp": 400,
            "pollutants": ["CO", "NO2", "AAI", "HCHO"]
        }
    }
]

def test_simulation(test_case):
    """Test a single simulation case"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_case['name']}")
    print(f"{'='*60}")
    print(f"Request data: {json.dumps(test_case['data'], indent=2)}")
    
    try:
        response = requests.post(API_URL, json=test_case['data'])
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(f"\nSummary:")
            print(json.dumps(result['summary'], indent=2))
            print(f"\nGrid points returned: {len(result['grid_data'])}")
            if len(result['grid_data']) > 0:
                print(f"\nFirst grid point example:")
                print(json.dumps(result['grid_data'][0], indent=2))
        else:
            print(f"\n❌ Error!")
            print(f"Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error!")
        print(f"Make sure the Flask server is running on port 5001")
        print(f"Run: python backend/app.py")
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")

def main():
    print("Fire Simulation API Test Suite")
    print("="*60)
    
    # Test each case
    for test_case in test_cases:
        test_simulation(test_case)
    
    print(f"\n{'='*60}")
    print("All tests complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
