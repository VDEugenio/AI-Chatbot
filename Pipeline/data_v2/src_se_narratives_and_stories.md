---
name: SRC Solutions Engineering Positioning
description: How Vaughn's SRC work maps to Solutions Engineering competencies — five positioning narratives. The full stories live in the referenced source files.
company: src
topics: [solutions_engineering, interview_prep, technical_communication]
skills: [stakeholder_communication, technical_liaison, requirement_negotiation]
story_types: [customer_collaboration, stakeholder_communication, cross_functional, technical_leadership, product_pitch]
related_files: [src_cop_is_king.md, src_tracksync_optimizations.md, src_tracksync_architecture.md, src_customer_engagement_onboarding.md]
---

## Key Narratives for Solutions Engineering Positioning

### 1. Technical Liaison & Cross-Functional Collaboration
- **TrackSync from day one:** Worked closely with a principal engineer in the OTA phase, then onboarded and mentored new engineers when the team grew
- **Customer collaboration:** Frequent conversations with military operator SMEs to define what "correct translation" even meant across two mismatched systems
- **Stakeholder presentations:** Led sprint demos and requirement discussions with military operators, program managers, and government contracting officers
- **"COP is King" socialization:** Proposed, refined, and presented a program-level decision framework to technical and non-technical audiences, getting buy-in at every level

### 2. Translating Technical Complexity for Non-Technical Audiences
- **"COP is King" as a communication win:** Took a complex data conflict problem and distilled it into a simple, actionable principle that program leadership could immediately understand and align around
- **Sprint demos to mixed audiences:** Presented technical progress to military operators (end users) and government stakeholders (decision-makers) in ways that were accessible and actionable
- **On-site customer engagement:** Demonstrated the system with real operational data, gathered feedback, and incorporated user needs into development priorities

### 3. Customer-Facing Problem-Solving
- **SME collaboration on translation logic:** Didn't just implement specs — actively worked with TAK and COP experts to determine effective data representations, iterating based on their feedback
- **On-site visits and real-data testing:** Plugged into production-like environments, gathered direct user feedback, and refined the system based on operational needs
- **Requirement gathering and negotiation:** Led discussions where technical constraints had to be balanced against customer expectations, proposing solutions and tradeoffs

### 4. Technical Depth & Systems Thinking
- **Owned core translation logic:** Built and optimized the heart of the TrackSync system, handling ~350K tracks/min in production
- **Identified architectural flaw (stateful table in stateless system):** Diagnosed a fundamental design problem and solved it with an elegant solution (embedding data in the message itself)
- **Performance optimization:** Parallelization, tree-based validation, and memory-efficient round-trip data handling
- **Scalability considerations:** Designed solutions that worked across multiple isolated TrackSync instances with different configurations

### 5. Onboarding & Knowledge Transfer
- **Created onboarding materials:** Built diagrams, presentations, and documentation to ramp up new engineers quickly
- **Domain knowledge transfer:** Taught new engineers not just the code, but the COP/TAK domain context necessary to contribute effectively
- **Advocacy for communication:** Championed open, frequent communication across teams and companies, creating a unified team dynamic even across organizational boundaries

The full narratives behind these themes are told once, in their canonical files: the "COP is King" decision framework in src_cop_is_king.md, the stateless round-trip solution in src_tracksync_optimizations.md, SME collaboration on translation logic in src_tracksync_architecture.md, and engineer onboarding in src_customer_engagement_onboarding.md.
