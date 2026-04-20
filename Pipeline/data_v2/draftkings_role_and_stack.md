---
name: DraftKings Role and Tech Stack
description: DraftKings Software Engineer role overview, DFS product context, team structure, and full technical stack (C#/.NET, Orleans, AWS, K8s, RabbitMQ, Redis).
company: draftkings
topics: [daily_fantasy_sports, distributed_systems, virtual_actor_model, microservices, tech_stack]
skills: [csharp, dotnet, orleans, aws, kubernetes, rancher, bamboo, sql, tsql, mysql, snowflake, redis, rabbitmq, aws_sqs, datadog, git, jira, feature_flags]
story_types: []
---

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
