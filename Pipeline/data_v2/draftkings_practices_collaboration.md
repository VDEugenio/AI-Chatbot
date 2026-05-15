---
name: DraftKings Code Quality, Cross-Functional Collaboration, and Career Direction
description: Sprint structure, code-review culture (separation of concerns, DI scoping, interfaces), testing practices, cross-functional collaboration with Product/Support/Sports Intelligence, personal contributions, career-direction reflection, and key scale metrics.
company: draftkings
topics: [code_review, separation_of_concerns, dependency_injection, agile, testing, cross_functional, career_direction, code_quality]
skills: [code_review, dependency_injection, interface_design, agile, testing, stakeholder_communication]
story_types: [technical_leadership, cross_functional, customer_collaboration, stakeholder_communication]
related_files: [draftkings_incident_response.md]
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

**Note:** Vaughn left DraftKings in February 2026 (laid off, RIF). This document reflects his experience there — it is not a current role.
**Contact:** Vaughn Eugenio | vaughndde@gmail.com
