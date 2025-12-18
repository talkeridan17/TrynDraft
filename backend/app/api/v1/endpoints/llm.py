from fastapi import APIRouter, HTTPException, Depends
from app.services.llm_analyst import LLMAnalystService
from app.services.draft_rules import DraftRulesService

router = APIRouter()
llm_analyst = LLMAnalystService()

@router.post("/analyze")
async def analyze_draft(request: dict):
    """Generate LLM analysis for current draft state."""
    try:
        draft_state = request.get("draftState", {})
        available_champions = request.get("availableChampions", [])
        top_recommendation = request.get("topRecommendation", "")
        
        if not available_champions:
            raise HTTPException(status_code=400, detail="No champions available")
        
        analysis = llm_analyst.generate_analysis(
            draft_state, 
            available_champions, 
            top_recommendation
        )
        
        return {
            "analysis": analysis,
            "top_recommendation": top_recommendation,
            "available_count": len(available_champions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape-and-train")
async def scrape_and_train(champions: list = None):
    """Scrape data for champions and prepare for LLM training."""
    # This would be called from an admin panel or cron job
    from app.services.content_scraper import ContentScraper
    from app.database import SessionLocal
    
    scraper = ContentScraper()
    db = SessionLocal()
    
    try:
        if not champions:
            # Default to top 20 champions by play rate
            champions = ["Aatrox", "Ahri", "Akali", "Alistar", "Amumu", 
                        "Anivia", "Annie", "Ashe", "AurelionSol", "Azir"]
        
        all_content = []
        for champion in champions:
            content = await scraper.scrape_for_champion(champion)
            all_content.extend(content)
        
        # Save to database (pseudo-code)
        # for item in all_content:
        #     db_content = models.ScrapedContent(**item)
        #     db.add(db_content)
        # db.commit()
        
        return {
            "scraped": len(all_content),
            "champions": champions,
            "message": f"Scraped {len(all_content)} content items"
        }
    finally:
        db.close()