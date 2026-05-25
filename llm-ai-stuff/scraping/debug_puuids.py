#!/usr/bin/env python3
"""
Debug script to identify why collect_puuids returns 0 PUUIDs
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path to import scraper
sys.path.insert(0, str(Path(__file__).parent))

from scraper import RiotClient, collect_puuids

# Set up logging to see detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

def test_puuid_collection():
    """Test PUUID collection with different tiers"""
    
    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        print("❌ RIOT_API_KEY not set!")
        print("Set it with: export RIOT_API_KEY=RGAPI-xxxx")
        return
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    client = RiotClient(api_key, platform="na1")
    
    # Test different tiers
    test_tiers = ["CHALLENGER", "GRANDMASTER", "MASTER", "EMERALD"]
    
    for tier in test_tiers:
        print(f"\n🔍 Testing {tier}...")
        try:
            puuids = collect_puuids(client, tier, max_summoners=5)
            print(f"   {tier}: {len(puuids)} PUUIDs collected")
            if puuids:
                print(f"   Sample PUUID: {list(puuids)[0][:20]}...")
        except Exception as e:
            print(f"   ❌ Error with {tier}: {e}")

def test_raw_endpoints():
    """Test raw API endpoints to see what they return"""
    
    api_key = os.environ.get("RIOT_API_KEY")
    if not api_key:
        return
    
    client = RiotClient(api_key, platform="na1")
    
    print(f"\n🔍 Testing raw endpoints...")
    
    # Test challenger endpoint
    print("\n--- Challenger ---")
    challenger = client.get_challenger_league()
    if challenger:
        print(f"✅ Got challenger data")
        print(f"   League: {challenger.get('league', {}).get('name', 'Unknown')}")
        print(f"   Tier: {challenger.get('league', {}).get('tier', 'Unknown')}")
        entries = challenger.get('entries', [])
        print(f"   Entries: {len(entries)}")
        if entries:
            first = entries[0]
            print(f"   First player: {first.get('summonerName', 'Unknown')}")
            print(f"   First player has summonerId: {bool(first.get('summonerId'))}")
    else:
        print("❌ No challenger data")
    
    # Test emerald endpoint
    print("\n--- Emerald IV ---")
    emerald = client.get_league_page("EMERALD", "IV", page=1)
    if emerald:
        print(f"✅ Got emerald data: {len(emerald)} entries")
        if emerald:
            first = emerald[0]
            print(f"   First player: {first.get('summonerName', 'Unknown')}")
            print(f"   First player has summonerId: {bool(first.get('summonerId'))}")
    else:
        print("❌ No emerald data")
    
    # Test summoner lookup
    print("\n--- Summoner lookup test ---")
    if challenger and challenger.get('entries'):
        first_entry = challenger['entries'][0]
        summoner_id = first_entry.get('summonerId')
        if summoner_id:
            print(f"Looking up summonerId: {summoner_id}")
            summoner = client.get_summoner_by_id(summoner_id)
            if summoner:
                print(f"✅ Got summoner data")
                print(f"   Name: {summoner.get('name', 'Unknown')}")
                print(f"   Has PUUID: {bool(summoner.get('puuid'))}")
                if summoner.get('puuid'):
                    print(f"   PUUID: {summoner['puuid'][:20]}...")
            else:
                print("❌ Failed to get summoner data")
        else:
            print("❌ No summonerId in first challenger entry")

if __name__ == "__main__":
    print("🚀 Debugging PUUID collection...\n")
    
    test_raw_endpoints()
    test_puuid_collection()
    
    print(f"\n📝 Check the logs above for detailed API responses")
