---
name: DraftKings On-Call and Incident Response (Early-Start Bug)
description: On-call rotation plus full narrative of the Titan early-start competition validation bug — 25-minute user resolution, root cause, fix, and logging improvements.
company: draftkings
topics: [on_call, incident_response, root_cause_analysis, validation_bug, customer_support, logging, observability]
skills: [datadog, debugging, root_cause_analysis, customer_impact_mitigation, csharp, dotnet]
story_types: [incident_response, customer_collaboration, problem_solving, cross_functional, technical_leadership]
related_files: [draftkings_architecture.md, draftkings_practices_collaboration.md]
---

## On-Call & Incident Response

### On-Call Structure
- **Rotation:** Participated in regular on-call rotation
- **Scope:** Triaging and resolving production incidents for DFS platform
- **Escalation:** Customer support → on-call engineer → engineering team as needed

### Critical Incident: Early-Start Competition Validation Bug

#### Background: Early-Start Competitions
An "early-start competition" occurs when a real-world game begins before its scheduled time:
- **Example:** Game scheduled for 8:00 PM actually starts at 7:50 PM
- **System Behavior:** DraftKings flags the competition as "early-start" to protect users
- **Business Rule:** Users can edit lineups until a player's game starts

#### The Bug

**Flawed Validation Logic (in Titan service):**
- When a user attempted a lineup edit (swap Player A for Player B), validation checked the ENTIRE lineup for early-start players
- **Problem:** If ANY player in the lineup was in an early-start competition, the ENTIRE edit was rejected - even if the swap itself was valid

**User Impact Scenario:**
1. User has Player C in their lineup (in an early-start competition - game already started)
2. User tries to swap Player A (game hasn't started) → Player B (game hasn't started)
3. Validation runs, detects Player C is in early-start competition
4. **Swap rejected incorrectly** - even though Player A and B are both legal to swap

#### Incident Timeline

**Discovery (T+0):**
- User contacted customer support reporting a rejected edit that should have been valid
- Customer support paged on-call engineer (me)

**Initial Diagnosis (T+0 to T+15min):**
- Examined Datadog logs for the user's validation failure
- Found validation reason: "Player in competition that has already started"
- Cross-referenced all players in user's lineup
- Identified Player C was in early-start competition, but Player A/B swap was valid
- **Root Cause:** Validation logic checking entire lineup instead of just swapped players

**Immediate Mitigation (T+15min to T+25min):**
- Used internal tools to manually adjust the user's lineup score and payout
- Wrote documentation of the manual adjustment
- Obtained necessary approvals
- Executed payout correction
- **User impact resolved in 25 minutes**

**Bug Fix (T+25min to T+2 days):**
- Created ticket and discussed solution with team
- **Fix:** Modified Titan service validation to check ONLY players being swapped in/out, not entire lineup
- Implemented fix myself (familiar with the issue from on-call investigation)
- **Accelerated through normal sprint cycle** (prioritized hotfix)
- Deployed fix approximately 2 days after ticket creation

**Prevention & Logging Improvements:**
- Enhanced logging verbosity for lineup validation failures
- **Specific Change:** Added more descriptive failure reasons to distinguish early-start issues from other validation failures
- **Old Log:** "Player in competition that has already started" (too generic)
- **New Log:** More specific context about which player, which competition, and why it was flagged as early-start
- **Impact:** Future similar issues can be diagnosed more quickly

#### Testing & Validation
- Used DraftKings internal testing tools to recreate the scenario
- Set up test contest with lineup containing early-start competition
- Verified fix allowed valid swaps while still blocking invalid ones

#### Scope Assessment
- **Single User Impact:** One-off report (early-start competitions are rare)
- **Small Window:** Issue only manifests during narrow time window when games start early
- **Low Recurrence Risk:** Combination of rare early-start + specific lineup edit timing

#### Key Takeaways
- **Customer Focus:** Prioritized user impact resolution (25min to manual payout) before implementing code fix
- **Root Cause Analysis:** Thorough log investigation to understand exact failure reason
- **Ownership:** Drove the entire incident from diagnosis → mitigation → fix → prevention
- **Cross-Team Collaboration:** Worked with customer support for initial triage, team for fix review
- **Proactive Prevention:** Improved logging to make future incidents easier to diagnose
