# Use Cases (Structured Format)

## Use Case: Generate Champion Recommendations

**Primary Actor:** Player  
**Preconditions:** User is in draft phase, enemy picks are visible  
**Main Success Scenario:**

1. System detects enemy champion selection
2. System retrieves current patch matchup data
3. System analyzes team composition requirements
4. System generates ranked recommendations
5. System displays recommendations with rationale

**Extensions:**

- 3a. Insufficient data available: System uses historical data with confidence indicator
- 4a. User has preferred champions: System prioritizes user proficiency

## Use Case: Manage User Preferences

**Primary Actor:** Registered User  
**Preconditions:** User is authenticated  
**Main Success Scenario:**

1. User accesses settings interface
2. System displays current preferences
3. User modifies champion pool settings
4. System validates and persists changes
5. System confirms successful update

**Extensions:**

- 3a. Invalid selection: System provides clear error message
- 4a. Storage unavailable: System caches locally and retries

## Use Case: Real-time Draft Sync

**Primary Actor:** System (automatic)  
**Preconditions:** User is in supported game client  
**Main Success Scenario:**

1. System detects draft session start
2. System establishes real-time connection
3. System mirrors draft state changes
4. System provides timely recommendations
5. System cleans up resources post-draft

**Extensions:**

- 2a. Connection failed: System falls back to manual input
- 3a. Data inconsistency: System performs reconciliation
