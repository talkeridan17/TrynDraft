# TrynDraft Development Roadmap

## Phase 1: Core Draft Interface (COMPLETED)
- [x] Draft UI with pick/ban slots
- [x] Champion picker with search
- [x] Phase-based system (BAN/PICK/COMPLETE)
- [x] Drag-and-drop functionality
- [x] Role and rank selection

## Phase 2: User Management (COMPLETED)
- [x] User registration and login
- [x] Profile page with settings
- [x] Champion pool management
- [x] Preferences (role, rank, profile picture)
- [x] Guest mode

## Phase 3: AI Integration (IN PROGRESS)
- [ ] LLM analysis refinement
- [ ] Neural network recommendation engine
- [ ] Champion statistics integration
- [ ] Matchup data analysis

## Phase 4: Data Collection
- [ ] Riot API integration for match data
- [ ] Champion win rates, pick rates, ban rates
- [ ] Matchup statistics
- [ ] Professional draft data

## Phase 5: Production Deployment
- [ ] CI/CD pipeline
- [ ] Cloud deployment (AWS/Railway)
- [ ] Monitoring and logging
- [ ] Performance optimization
- [ ] Beta testing

## Phase 6: Advanced Features
- [ ] Draft history
- [ ] Draft sharing
- [ ] Multi-user live drafts
- [ ] Mobile responsive design


we hit the limit pls continue where you left off. Also, I want to add the extention I talked about beforehand to the frontend now with seperating the profile and settings page into seperate pages, since now I just got a new API key for the proffessional league of legends data (I added it to the .env in backend). It is part of the cloud9 x jetbrains hackathon, so pls add the settings page to the frontend where the user can now select the game mode they are in (ranked, clash, or pro), and if they are clash or pro allow them to set a bunch of data for their opponents, and for pro use the data from the new api key as well as the soloq data for the picker and LLM now, and for the clash do the same with allowing user to secet his opponents role and setting their champ pools too, and update the draft page accordignly to the mode they are in. I know these are a lot of changes and we still need to fix the current issues in the draft, so pls take all of this super slow. I don't want to break what we already have, I want to improve it, and fix the current bugs with the entire thing that happened since we started integrating the backend. Also, pls do the thing i told you with the scrapers, I want ou to create a logger file somewhere in the root directory that both scrapers of textual and statistical data will write to (or two log files if you think that is more fitting), and they will keep me updated on the scraping process, which should be always ongoing both during this local stage and obviosuly on timed intervals when in production. So pls keep going with he fixes and add these changes, remeber i like the current profile page so don't change it, just add a new settings page now that got a similar style, and connect all the pages togther with whatver buttons and connections necessary. if a user is logged in as a guest, clicking the profile page should direct him to login page but clicking the settings page is completely fine. 