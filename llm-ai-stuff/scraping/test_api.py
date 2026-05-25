#!/usr/bin/env python3
"""
Test script to debug Riot API connectivity and authentication
"""

import os
import requests
import json

def test_api_key():
    """Test if the API key is valid and working"""
    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        print("❌ RIOT_API_KEY environment variable not set")
        print("Set it with: export RIOT_API_KEY=RGAPI-xxxx")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    # Test basic connectivity to Riot API
    headers = {"X-Riot-Token": api_key}
    
    # Test a simple endpoint - account info (should work for any valid key)
    test_urls = [
        "https://na1.api.riotgames.com/lol/status/v4/platform-data",  # Platform status
        "https://americas.api.riotgames.com/lol/match/v5/matches",    # Match endpoint (will 404 but tests auth)
    ]
    
    for url in test_urls:
        try:
            print(f"\n🔍 Testing: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            # Check rate limit headers
            app_limit = response.headers.get("X-App-Rate-Limit", "Not present")
            app_count = response.headers.get("X-App-Rate-Limit-Count", "Not present")
            method_limit = response.headers.get("X-Method-Rate-Limit", "Not present")
            method_count = response.headers.get("X-Method-Rate-Limit-Count", "Not present")
            
            print(f"   App Rate Limit: {app_limit}")
            print(f"   App Rate Count: {app_count}")
            print(f"   Method Rate Limit: {method_limit}")
            print(f"   Method Rate Count: {method_count}")
            
            if response.status_code == 200:
                print("   ✅ Success!")
                return True
            elif response.status_code == 403:
                print("   ❌ 403 Forbidden - API key likely expired or invalid")
                print("   Get a new key at: https://developer.riotgames.com")
                return False
            elif response.status_code == 404:
                print("   ✅ 404 Expected - API key is valid (endpoint doesn't exist)")
                return True
            else:
                print(f"   ⚠️  Unexpected status: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
            return False
    
    return False

def test_real_endpoint():
    """Test a real endpoint that should return data"""
    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        return False
    
    headers = {"X-Riot-Token": api_key}
    
    # Test getting challenger ladder (should always have data)
    url = "https://na1.api.riotgames.com/lol/league/v4/challengerleagues/queues/RANKED_SOLO_5x5"
    
    try:
        print(f"\n🔍 Testing real endpoint: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            league = data.get("league", {})
            print(f"   ✅ Success! League: {league.get('name', 'Unknown')}")
            print(f"   Tier: {league.get('tier', 'Unknown')}")
            print(f"   Queue: {league.get('queue', 'Unknown')}")
            entries = data.get("entries", [])
            print(f"   Players in challenger: {len(entries)}")
            return True
        else:
            print(f"   ❌ Failed: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Riot API connectivity...\n")
    
    if test_api_key():
        print("\n✅ API key test passed!")
        test_real_endpoint()
    else:
        print("\n❌ API key test failed!")
        print("\nNext steps:")
        print("1. Get a valid API key from https://developer.riotgames.com")
        print("2. Set environment variable: export RIOT_API_KEY=RGAPI-xxxx")
        print("3. Run this test again")
