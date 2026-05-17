#!/usr/bin/env python3
"""
Debug script to test JSearch API
"""

import os
import requests
import json

API_KEY = os.environ.get("JSEARCH_API_KEY", "")

print(f"API Key present: {'Yes' if API_KEY else 'No'}")
print(f"API Key length: {len(API_KEY) if API_KEY else 0}")

if not API_KEY:
    print("ERROR: JSEARCH_API_KEY not set!")
    exit(1)

print("\n" + "="*70)
print("Testing JSearch API Connection")
print("="*70)

url = "https://jsearch.p.rapidapi.com/search"
headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "jsearch.p.rapidapi.com"
}
params = {
    "query": "Software Engineer in Ohio, US",
    "date_posted": "today",
    "employment_types": "FULLTIME",
    "page": 1,
    "num_pages": 1,
}

print(f"\nURL: {url}")
print(f"Headers: {{'x-rapidapi-key': 'HIDDEN', 'x-rapidapi-host': '{headers['x-rapidapi-host']}'}}")
print(f"Params: {params}")

print("\nMaking API request...")
try:
    response = requests.get(url, headers=headers, params=params, timeout=15)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body (first 1000 chars):")
    print(response.text[:1000])
    
    if response.status_code == 200:
        data = response.json()
        jobs = data.get("data", [])
        print(f"\n✅ API SUCCESS - Found {len(jobs)} jobs")
        if jobs:
            print(f"\nFirst job:")
            print(json.dumps(jobs[0], indent=2)[:500])
    else:
        print(f"\n❌ API ERROR - Status {response.status_code}")
        print(f"Error message: {response.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
