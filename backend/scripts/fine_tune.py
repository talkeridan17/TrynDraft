#!/usr/bin/env python3
"""
Fine-tuning script for TrynDraft.
Run this manually when you want to update the model.
"""
import asyncio
import os
import json
from datetime import datetime

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import LLMService

async def main():
    print("🚀 Starting TrynDraft Fine-tuning Process")
    print("=" * 50)
    
    # 1. Initialize service
    llm = LLMService()
    
    # 2. Champions to scrape
    champions = [
        "Aatrox", "Ahri", "Akali", "Alistar", "Amumu",
        "Annie", "Ashe", "Caitlyn", "Darius", "Ezreal"
    ]
    
    print(f"📊 Scraping data for {len(champions)} champions...")
    
    # 3. Scrape data
    all_data = []
    for champion in champions:
        print(f"  - Scraping {champion}...")
        data = await llm.scrape_champion_data(champion)
        all_data.extend(data)
        await asyncio.sleep(1)  # Be nice to servers
    
    print(f"✅ Scraped {len(all_data)} data items")
    
    # 4. Prepare training data
    training_data = llm.prepare_training_data(all_data)
    print(f"📝 Prepared {len(training_data)} training examples")
    
    # 5. Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"training_data_{timestamp}.jsonl"
    
    with open(filename, 'w') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')
    
    print(f"💾 Saved training data to {filename}")
    print("\n🎯 NEXT STEPS:")
    print("1. Go to huggingface.co")
    print("2. Create an account and get API token")
    print("3. Upload", filename, "as a dataset")
    print("4. Fine-tune Mistral-7B on your dataset")
    print("5. Set FINE_TUNED_MODEL_ID environment variable")
    print("\n⚠️  Fine-tuning costs money on HuggingFace!")
    print("   - About $5-10 for small dataset")

if __name__ == "__main__":
    asyncio.run(main())