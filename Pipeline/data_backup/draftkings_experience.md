# DraftKings Software Engineer Experience
## Comprehensive Work Context Documentation

---

## Role Overview

**Company:** DraftKings  
**Position:** Software Engineer  
**Duration:** May 2025 – February 2026 (9 months)  
**Location:** Remote  
**Team:** DFS (Daily Fantasy Sports) Backend Engineering  
**Team Size:** 5 engineers + 1 engineering manager  
**Reporting Structure:** 
- First few months: Reported to engineering manager
- Later months: Reported to a principal engineer transitioning to management

---

## Product Context: Daily Fantasy Sports (DFS)

### What is DFS?
Daily Fantasy Sports is DraftKings' core product where users compete in short-term fantasy contests (typically lasting one day to one week). Key characteristics:

- **Contest Structure:** Users draft virtual teams of real athletes using a $50,000 salary cap
- **Scoring:** Athletes earn points based on real-world performance (touchdowns, yards, hits, rebounds, etc.)
- **Prize System:** Users win cash prizes based on lineup performance - no season-long commitment
- **Scale:** 500,000+ peak daily active users
- **Sports Coverage:** NFL, MLB, NBA, NHL, PGA, Soccer, MMA, NASCAR, College sports, eSports

### User Flow
1. Browse contest lobby (filter by sport, prize pool, contest type)
2. Enter a contest (free or paid entry)
3. Draft a lineup within salary cap constraints
4. Watch real-time scoring as games progress
5. Check standings and collect winnings

### Technical Significance
DFS requires real-time, high-throughput systems handling:
- Lineup creation and validation
- Real-time scoring updates
- Contest entry management
- Payout calculations
- Player eligibility and roster constraints

---

## Technical Stack

### Languages & Frameworks
- **Primary:** C# / .NET
- **Actor Framework:** Microsoft Orleans (for some services)
- **APIs:** REST APIs for client communication

### Infrastructure & DevOps
- **Cloud:** AWS
- **Orchestration:** Kubernetes (manual scaling based on traffic forecasts)
- **Container Management:** Rancher
- **CI/CD:** Bamboo

### Data & Messaging
- **Databases:** SQL, T-SQL, MySQL, Snowflake
- **Caching:** Shared Redis cluster
- **Messaging:** 
  - Primary: RabbitMQ (95% of service-to-service communication)
  - Secondary: AWS SQS (used sparingly)

### Monitoring & Tooling
- **Observability:** Datadog
- **Version Control:** Git
- **Project Management:** Jira
- **Feature Flags:** Stored in app settings, configurable per environment

### Microsoft Orleans Context
Orleans is a distributed systems framework using the **Virtual Actor Model**:
- **Grains:** Virtual actors with identity, behavior, and state
- **Always Addressable:** Grains always exist virtually, automatically instantiated when needed
- **Automatic Management:** Runtime handles actor placement, load balancing, failure recovery
- **Use Case at DraftKings:** Managing distributed state for millions of user lineups, contests, and real-time scoring across servers

---

## Service Architecture

The DFS platform consists of 15+ distributed microservices. Key services include:

### Abacus
- **Purpose:** Payout calculation and payout flow
- **Communication:** Uses RabbitMQ to query Scores service for user contest placement

### Titan
- **Purpose:** Lineup and entry validation
- **Responsibilities:** 
  - Validate lineup composition (salary cap, roster constraints, player eligibility)
  - Handle edit validations (ensure users can only edit valid lineups)
  - Early-start competition logic

### Scoreboard
- **Purpose:** Data flow of game scores from external providers to customers
- **Integration:** Receives feeds from Sports Intelligence team
- **Significance:** Parses and distributes real-time scoring data across platform

### Scores
- **Purpose:** Calculate individual user lineup scores
- **Integration:** Receives game data from Scoreboard, calculates fantasy points based on player performance

### Inter-Service Communication Pattern
- **Messaging:** RabbitMQ for asynchronous, reliable service-to-service communication
- **Benefits:** Ensures reliability, timeliness, correct load balancing
- **Example:** Abacus → RabbitMQ → Scores (to determine user placement for payout calculation)

---

## Performance & Scale

### Traffic Patterns
- **Peak Users:** 500,000+ daily active users during peak seasons
- **Seasonal Variance:** Traffic varies drastically by sport season
  - **High Traffic:** Week 1 NFL, playoff seasons, major sporting events
  - **Low Traffic:** Off-seasons (e.g., NFL off-season)
- **Throughput:** Systems designed to handle high-volume, time-sensitive workflows

### Performance Optimization Work

#### Redis Caching Implementation
- **Use Case:** Player card data during drafts
- **Problem:** Many users querying same player stats simultaneously during draft windows
- **Solution:** Cached frequently-requested player card data to reduce database load and improve response times
- **Impact:** Reduced resource usage, faster player card load times

#### Database Query Optimization
- **Approach:** Made more specific database calls to retrieve only necessary data
- **Techniques:** 
  - Narrowed SELECT statements to required columns
  - Leveraged cached data where appropriate
  - Reduced payload sizes
- **Result:** More efficient database calls, improved query performance

#### Kubernetes Scaling
- **Approach:** Scaled workloads up/down based on seasonal traffic forecasts
- **Process:** Manual scaling adjustments to match predicted demand
- **Example:** Scale up before Week 1 NFL, scale down during off-season
- **Impact:** Maintained platform stability during peak demand while optimizing costs during low-traffic periods

---

## Major Projects & Technical Challenges

### Project: Shohei Ohtani Dual-Role Support

#### Context
Shohei Ohtani is a unique MLB player who plays both as a pitcher and a hitter - a rare dual-role scenario in modern baseball. This created a significant edge case in DFS gameplay.

#### The Problem
- Ohtani was accumulating points for BOTH pitching and hitting performances in the same game
- Users drafting Ohtani could earn significantly more points than intended
- This created an unfair competitive advantage and violated DFS game balance

#### The Solution
**Technical Implementation:**
- Created two separate "Draftables" for Ohtani: one for pitching, one for hitting
- Users must choose which role to draft (cannot have both simultaneously)
- Required database schema changes to support multiple draftable entities for a single player

**Solution Pitch & Technical Communication:**
- **I pitched this dual-draftable solution** to DFS engineering, Product, and cross-functional teams
- Explained the technical approach in terms each audience could understand:
  - **Engineering Teams:** Database schema changes, service modifications, data flow impact
  - **Product Team:** User experience implications, how dual-draftables would appear in UI, business logic constraints
  - **Sports Intelligence:** Data feed requirements to differentiate pitching vs. hitting stats
  - **Shared Database Teams:** Schema migration strategy, backward compatibility considerations
- Translated complex technical concepts (database normalization, draftable entity relationships) into business terms (fair gameplay, user choice, competitive balance)
- Facilitated alignment across teams with different priorities and technical backgrounds

**Cross-Functional Coordination:**
- **Product Team:** Defined how dual-role players should be displayed and selected in the UI
- **Sports Intelligence Team:** Provided data feeds differentiating pitching stats from hitting stats for the same player
- **Shared Database Teams:** Coordinated schema changes with other teams relying on player data

#### Timeline & Status
- **Trigger:** Implemented reactively once Ohtani began playing (not proactive)
- **Status:** Project was ongoing when I left DraftKings (still being refined)
- **Significance:** This edge case likely applies to future dual-role players, making the solution reusable

#### Technical Learning
- Demonstrated ability to identify edge cases that impact user experience
- **Showcased technical communication skills** by pitching solution across engineering, product, and data teams with different technical backgrounds
- Translated complex database and architecture concepts into business terms (fair gameplay, competitive balance)
- Required cross-team coordination across engineering, product, and data teams
- Highlighted the complexity of real-world sports rules in software systems

---

### Feature Flagging Strategy

#### Implementation
- **Storage:** Feature flags stored in app settings (not external service like LaunchDarkly)
- **Configuration:** Flags set per environment (dev, staging, prod)
- **Granularity:** Could enable/disable entire features or individual sub-features

#### Use Cases

**1. Safe Rollouts**
- Enable new features gradually (e.g., start with 10% of users, ramp to 100%)
- Test features in production with limited exposure
- Quick rollback capability if issues arise

**2. Redis Caching Toggles**
- Feature flag to enable/disable Redis caching per service
- Allowed A/B testing of caching strategies
- Enabled quick disabling if cache corruption occurred

**3. Emergency Kill Switches**
- If a feature caused production issues, could disable via flag without redeploying
- Critical for time-sensitive DFS workflows where downtime = lost revenue

**Example Scenario:**
- Deploy major feature to prod with flag OFF
- Gradually enable for internal testing
- Enable for 10% of users
- Monitor Datadog metrics (error rates, latency, throughput)
- If metrics look good → ramp to 100%
- If issues arise → disable flag immediately, investigate offline

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

---

## Code Quality & Development Practices

### Sprint Structure
- **Sprint Length:** 2-week sprints
- **Ceremonies:**
  - Daily standups
  - Weekly refinement sessions
  - Ad hoc refinement as needed
  - Sprint planning, reviews, retrospectives (standard Agile)

### Code Review Culture
DraftKings emphasized readable, maintainable code. Code reviews were rigorous and focused on:

#### 1. Separation of Concerns
- **Business Logic Placement:** Ensure business logic is NOT in mapping classes or DTOs
- **Mapping Classes:** Should only handle data transformation, no decisions or calculations
- **Service Layer:** Business logic belongs in service classes, not controllers or mappers

#### 2. Dependency Injection & Scoping
- **Manager Scoping:** Ensure managers (service layer) were correctly scoped (singleton, scoped, transient)
- **Lifecycle Management:** Verify dependencies had appropriate lifetimes for their use case

#### 3. Interface Usage
- **Abstraction:** Classes should have interfaces when they represent behaviors that could vary
- **Testability:** Interfaces enable mocking and unit testing
- **Extensibility:** Makes future refactoring easier

#### 4. General Patterns
- Avoid code duplication (DRY principle)
- Clear naming conventions
- Proper error handling and logging
- Performance considerations (avoid N+1 queries, unnecessary allocations)

### Testing Practices
- Functional testing before merging
- Extensive ticket refinement to clarify acceptance criteria
- Iterative testing to improve software quality and maintainability
- Internal tools for setting up test scenarios (contest simulation, early-start scenarios, etc.)

---

## Cross-Functional Collaboration

### Engineering Teams
- **Frontend Team:** Coordinated on UI changes, API contracts, feature rollouts
- **Other Backend Teams:** Collaborated on shared database schemas, service integrations

### Product Team
- **Requirements Gathering:** Partnered with PM on feature definitions
- **Progress Communication:** Translated technical progress into business terms
- **Feature Prioritization:** Provided technical input on feasibility and effort estimates

### Customer Support
- **On-Call Escalations:** Received pages from support for production issues
- **User Impact Mitigation:** Worked directly with support to resolve user-facing problems
- **Issue Reporting:** Support provided valuable user feedback on edge cases and bugs

### Sports Intelligence Team
- **Data Integration:** Received real-time sports data feeds
- **Edge Case Identification:** Collaborated on handling unusual sports scenarios (e.g., Ohtani dual-role)
- **Feed Format Specification:** Ensured data feeds matched system expectations

---

## Personal Contributions & Growth

### Technical Contributions
- Engineered and maintained 15+ distributed microservices
- Implemented Redis caching for performance optimization
- Built and optimized database queries for efficiency
- Led incident response and root cause analysis
- Designed event-driven communication patterns with RabbitMQ
- Scaled Kubernetes workloads based on traffic forecasts

### Cross-Functional Impact
- Served as technical liaison between engineering, product, and customer support
- Identified and drove resolution of the Ohtani dual-role edge case
- Communicated technical complexity to non-technical stakeholders
- Participated in on-call rotation, ensuring platform reliability for 500k+ users

### Code Quality & Best Practices
- Performed extensive code reviews to maintain code quality
- Improved logging and observability for future debugging
- Contributed to team standards for maintainable, testable code

### Problem-Solving Approach
- Methodical debugging using logs and metrics (Datadog)
- Prioritized user impact over "perfect" solutions (manual payout first, code fix second)
- Proactive prevention mindset (improved logging after incident)
- Ownership of issues from discovery through resolution

---

## Technical Interests & Career Direction

Throughout my time at DraftKings, I consistently gravitated toward the customer-facing and cross-functional aspects of software engineering:

- **Incident Response:** Thrived in on-call scenarios requiring quick diagnosis and user-focused mitigation
- **Cross-Team Projects:** Most engaged during Ohtani project where I coordinated across product, data, and engineering
- **Stakeholder Communication:** Enjoyed translating technical concepts for non-technical partners
- **User Impact Focus:** Prioritized customer experience (e.g., 25min manual payout resolution)

This experience reinforced my interest in **Solutions Engineering roles** where technical depth meets customer-facing problem-solving.

---

## Key Metrics & Scale

- **Platform Users:** 500,000+ peak daily active users
- **Services Maintained:** 15+ distributed microservices
- **Tech Stack:** C#, .NET, Microsoft Orleans, AWS, Kubernetes, RabbitMQ, Redis, SQL
- **Incident Resolution:** 25-minute user impact resolution on critical validation bug
- **Cross-Functional Projects:** Led Ohtani dual-role player support across engineering, product, and data teams

---

## End Notes

This document represents 9 months of backend engineering experience at DraftKings, focusing on distributed systems, real-time data processing, and high-availability services for a large-scale consumer platform. The role emphasized technical depth, operational excellence, and cross-functional collaboration - all foundational skills for Solutions Engineering and Solutions Architect roles.

**Last Updated:** April 2026  
**Contact:** Vaughn Eugenio | vaughndde@gmail.com
