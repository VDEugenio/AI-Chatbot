---
name: DraftKings Service Architecture
description: DFS platform's 15+ microservices — Abacus (payouts), Titan (validation), Scoreboard (score ingestion), Scores (lineup scoring) — and the RabbitMQ-based inter-service communication pattern.
company: draftkings
topics: [microservices, distributed_systems, event_driven, inter_service_communication, payouts, validation, real_time_scoring]
skills: [rabbitmq, rest_apis, distributed_systems_design]
story_types: [architecture_design, systems_thinking]
related_files: [draftkings_role_and_stack.md, draftkings_performance_scale.md]
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
