---
name: DraftKings Ohtani Dual-Role Player Project
description: Cross-functional project to support Shohei Ohtani's pitcher+hitter dual role in DFS — Vaughn pitched the dual-Draftable solution across engineering, product, sports intelligence, and DB teams.
company: draftkings
topics: [edge_cases, dual_role_players, database_schema, cross_functional, product_pitch, fantasy_sports]
skills: [sql, database_design, stakeholder_communication, cross_team_coordination]
story_types: [product_pitch, cross_functional, stakeholder_communication, customer_collaboration, problem_solving]
related_files: [draftkings_architecture.md, draftkings_performance_scale.md, draftkings_incident_response.md]
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
