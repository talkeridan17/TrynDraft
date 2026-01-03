#!/usr/bin/env python3
"""
Script to scrape textual data for LLM fine-tuning.
Run this to collect guide/discussion text for champions.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.text_scraper import scrape_champions_for_llm

async def main():
    print("🚀 Starting TrynDraft Text Data Scraper")
    print("=" * 60)
    print("Purpose: Collect textual data for LLM fine-tuning")
    print("Sources: Mobafire guides, Reddit discussions, Fandom wiki")
    print("=" * 60)
    
    # Define champions to scrape
    champions = [
        "Aatrox", "Ahri", "Akali", "Alistar", "Amumu",
        "Annie", "Ashe", "Blitzcrank", "Brand", "Caitlyn",
        "Darius", "Draven", "Ezreal", "Fiora", "Garen",
        "Jax", "Jhin", "Jinx", "Katarina", "Lee Sin",
        "Lux", "Malphite", "Master Yi", "Miss Fortune",
        "Morgana", "Nautilus", "Orianna", "Pyke", "Riven",
        "Shaco", "Sona", "Teemo", "Thresh", "Tryndamere",
        "Twisted Fate", "Vayne", "Veigar", "Yasuo", "Zed",
        "Zoe"
    ]
    
    print(f"\n📊 Will scrape text data for {len(champions)} champions")
    print("⚠️  This will take 30-60 minutes (respecting rate limits)")
    print("\nStarting now...\n")
    
    try:
        # Run the scraper
        scraped_data = await scrape_champions_for_llm(champions)
        
        print("\n" + "=" * 60)
        print("✅ Text Data Scraping Complete!")
        print(f"📁 Collected {len(scraped_data)} text chunks")
        
        # Save summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = f"scraping_summary_{timestamp}.json"
        
        summary = {
            "total_chunks": len(scraped_data),
            "champions_scraped": len(champions),
            "sources": ["mobafire_guides", "reddit_discussions", "fandom_wiki"],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📝 Summary saved to: {summary_file}")
        print("\n💡 Next steps:")
        print("1. Check 'scraped_text_data/' folder for JSON files")
        print("2. Use data for LLM fine-tuning")
        print("3. Run this script weekly to keep data fresh")
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())