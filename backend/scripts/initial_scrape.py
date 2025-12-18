# scripts/initial_scrape.py
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.content_scraper import ContentScraper
from app.services.data_dragon import DataDragonService
from app.database import SessionLocal
from app import models
from datetime import datetime

async def scrape_champion_data():
    """Scrape initial champion data."""
    scraper = ContentScraper()
    data_dragon = DataDragonService()
    db = SessionLocal()
    
    try:
        print("Fetching champion data from Data Dragon...")
        champions = await data_dragon.get_champion_data()
        
        for champ_id, champ_data in champions.items():
            print(f"Processing {champ_data['name']}...")
            
            # Check if champion already exists
            existing = db.query(models.Champion).filter(
                models.Champion.id == champ_id
            ).first()
            
            if existing:
                # Update existing
                existing.name = champ_data['name']
                existing.key = champ_data['key']
                existing.title = champ_data.get('title', '')
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                champion = models.Champion(
                    id=champ_id,
                    name=champ_data['name'],
                    key=champ_data['key'],
                    title=champ_data.get('title', ''),
                    roles=champ_data.get('tags', []),
                    patch=await data_dragon.get_latest_version(),
                    updated_at=datetime.utcnow()
                )
                db.add(champion)
            
            # Scrape additional content
            content = await scraper.scrape_for_champion(champ_data['name'])
            
            for item in content[:5]:  # Limit to 5 items per champion
                scraped = models.ScrapedContent(
                    source=item['source'],
                    url=item['url'],
                    title=item['title'],
                    content=item['content'],
                    champion=item['champion'],
                    tags=item['tags'],
                    patch_version=item.get('patch_version', '14.4'),
                    created_at=datetime.utcnow()
                )
                db.add(scraped)
        
        db.commit()
        print(f"Successfully scraped data for {len(champions)} champions")
        
    except Exception as e:
        db.rollback()
        print(f"Error during scraping: {e}")
        raise
    finally:
        db.close()

async def main():
    """Main function to run all initial scraping tasks."""
    print("Starting initial data scraping...")
    
    # Create cache directory
    os.makedirs("data_cache", exist_ok=True)
    
    # Run scraping tasks
    await scrape_champion_data()
    
    print("Initial scraping completed!")

if __name__ == "__main__":
    asyncio.run(main())