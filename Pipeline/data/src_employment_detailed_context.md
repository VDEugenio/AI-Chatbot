# SRC Inc. — Software Engineer
**October 2023 – May 2025 (19 months)**  
**Location:** North Charleston, SC (Hybrid)  
**Security Clearance:** Secret (obtained during full TrackSync contract, expires ~June 2026)

---

## Role Overview

Vaughn worked as a Software Engineer at SRC Inc., a defense contractor, contributing to two primary projects: **TrackSync** (a real-time military track exchange middleware platform) and **COMET** (a task management web application for Marine workflows). His work spanned backend development, frontend UI, cross-functional stakeholder collaboration, technical leadership, and customer-facing engagement with military operators and program stakeholders.

### Team Structure
- **Team size:** 4 engineers at peak (1 principal engineer + 3 junior engineers, including Vaughn)
- **Reporting structure:** Reported directly to a Project Manager who handled both TrackSync and COMET contracts (PM was somewhat technical but primarily program/business-focused)
- **Collaboration:** Worked closely with the principal engineer (tech lead, collaborative on architecture decisions), other junior engineers, and external subcontractors from other contracting companies on COMET

### Timeline Breakdown
1. **Oct 2023 – Jan/Feb 2024 (~4 months):** TrackSync OTA (Other Transaction Authority) — MVP phase with just Vaughn and the principal engineer
2. **Feb/May 2024 – May/Jun 2024 (~3-4 months):** COMET contract
3. **Jun 2024 – May 2025 (~12 months):** TrackSync full contract — team grew to 4 engineers; Vaughn onboarded new engineers, polished the system, and conducted preliminary research for a potential TrackSync V2

---

## TrackSync: Real-Time Military Track Exchange Middleware

### What TrackSync Does
TrackSync is a **stateless, real-time middleware platform** that enables secure track exchange between two military situational awareness systems:
- **TAK (Team Awareness Kit):** Field-level situational awareness tool used by soldiers and operators on the ground, showing real-time position data for personnel and assets directly from devices in the field
- **COP (Common Operating Picture):** Command-level unified view used by senior military leadership to make operational decisions, aggregating data from multiple sources including TAK and representing the authoritative synchronized picture across an entire operation

**Core function:** TrackSync translates position data ("tracks") between TAK and COP, handling ~**350,000 tracks per minute** in production.

### Architecture
- **TrackSync internal structure:** Runs both a COP server and a TAK server internally
- **Data flow:**
  - External COP clients send tracks → TrackSync's COP server → **in-memory Java queue**
  - External TAK clients send tracks → TrackSync's TAK server → **in-memory Java queue**
  - Translation logic pulls from queues, translates, and sends to the opposite server
  - Opposite server pushes translated tracks out to its clients
- **Deployment:** Multiple isolated instances of TrackSync run simultaneously because different operators/teams need different configurations for their units (not for load balancing, but for operational customization)
- **Stateless design:** No database; all processing is in-memory

### Vaughn's Primary Ownership: Translation Logic
Vaughn **owned the core translation piece** — the logic responsible for converting track data between TAK and COP formats once data was ingested from either system.

**Why translation was complex:**
- **Mismatched formats:** TAK and COP used completely different data structures and representations for the same concepts
- **Missing data and fields:** Frequent gaps in data from both systems
- **Complete representational mismatch:** The two systems didn't just differ in format — they fundamentally represented tracks differently
- **Customer collaboration required:** Vaughn frequently spoke with subject matter experts (SMEs) from both TAK and COP — military operators who used these systems daily — to determine how to accurately translate data into formats they found effective

**SME collaboration workflow:**
- **Early phase:** Bi-weekly conversations with SMEs (aligned with 2-week sprint cadence)
- **Later phase:** Ad-hoc conversations as Vaughn built deeper relationships and domain knowledge
- **Typical interaction:** Vaughn would show COP data to a TAK SME and ask, "How would this be represented in TAK?" (and vice versa)
- **Negotiating tradeoffs:** Initially had to push back or propose options when TAK and COP had incompatible representations, which led to the creation of the **"COP is King" principle** (see below)

### Key Technical Optimizations

#### (A) Tree-Based ID Validation
**Problem:** TrackSync received a very long string ID for each track used for verification and categorization. The system frequently received noise or dummy data. Each character in the ID had a specific meaning and sub-categorization, and the next character could only be from a certain set of characters based on the previous character.

**Solution:** Vaughn built a **tree structure** (likely a prefix tree/trie) that allowed the system to verify and categorize IDs much faster by leveraging the character dependency rules.

**Impact:** Drastically improved validation speed (exact metrics not recalled, but improvement was significant).

#### (B) Parallelization of Translation
**Problem:** With ~350K tracks/min throughput in production, translation logic had to be as efficient as possible.

**Solution:** Implemented **parallelization** for the translation process to handle high-volume real-time data flow.

#### (C) Embedding COP Precision Data in TAK Tracks (Stateless Round-Trip Solution)
**Problem:** COP stored more precise data about tracks than TAK. When sending tracks from COP → TAK, some resolution was lost. When TAK sent that same track back to COP, the system needed to restore the original precision.

**Original approach:** Maintained a **lookup table in TrackSync** to track the extra COP data for each track.

**Why the table approach failed:**
- The table could **grow very quickly**, causing performance issues
- TrackSync was **stateless** and had **no database**
- **Multiple isolated instances** of TrackSync ran simultaneously (different operator configurations), so a shared table would've been a nightmare
- TrackSync **crashes** would lose all table data

**Vaughn's solution:** Instead of maintaining an external stateful table, **embed the extra COP precision data in a custom field within the TAK track itself**. When the track was sent from COP → TAK, the additional COP-specific data was stored in a custom field that TAK would preserve. When TAK sent the track back through TrackSync to COP, the system extracted that data from the custom field and repopulated the full COP representation.

**Impact:**
- Eliminated the stateful table entirely
- Improved **redundancy** (data traveled with the track, not in external state)
- Improved **efficiency** (no table lookups, no growing memory footprint)
- Worked seamlessly across **multiple TrackSync instances**
- **When implemented:** Start of the full TrackSync contract (~June 2024)

---

## "COP is King" Principle

### The Problem
Because TrackSync ingested position data from both TAK (field-level, granular, direct from devices) and COP (command-level, aggregated, authoritative), **discrepancies** between the two sources created ambiguity:
- Which source should be trusted when TAK and COP show conflicting positions for the same asset?
- Conflicts arose due to timing differences, connectivity issues, or data gaps
- This wasn't just a technical problem — it affected **integration requirements, subcontractor deliverables, and customer expectations**

### Vaughn's Solution: "COP is King"
After observing **repeated conflicts**, Vaughn proposed a simple, program-level principle:

> **The COP is always the source of truth. If TAK and COP show conflicting data, COP wins — full stop.**

This meant:
- No manual conflict resolution required
- No data conflict escalation
- Clear, unambiguous decision framework for the entire program

### Socialization Process
Vaughn didn't just implement this as a technical decision — he **socialized it bottom-up** across multiple stakeholder groups:

1. **Principal engineer and PM:** Presented the idea first, gathered feedback
2. **SMEs (military operators):** Created a small presentation, incorporated their input
3. **Stakeholders (program managers, government contracting officers):** Presented the refined principle to program leadership

**Result:** The principle was adopted program-wide and referenced repeatedly by stakeholders. It gave program leadership **something they could align around immediately**, preventing weeks of ambiguity and rework.

### Edge Cases and Exceptions
The principle was **mostly absolute**, but with pragmatic exceptions:
- If TrackSync received a **certain amount of congruent updates from TAK**, it could override the COP-is-King rule **for a very small sector of the data** for each track
- These exceptions were defined collaboratively with SMEs and stakeholders

### Why This Story Matters for Solutions Engineering
This demonstrates **exactly what SE and SA roles require:**
- Taking a **technically complex problem** (data conflicts across systems)
- Understanding the **business and operational context** (program requirements, customer expectations, integration dependencies)
- Translating it into a **clear decision framework** that non-technical stakeholders could immediately understand and act on
- **Socializing the solution** across technical and non-technical audiences
- **Incorporating feedback** iteratively before final adoption

---

## Technical Stack (TrackSync)

### Backend
- **Language:** Java
- **Framework:** Spring Boot
- **Messaging:** In-memory Java queues (e.g., `ConcurrentLinkedQueue`)
- **Containerization:** Podman
- **Logging:** log4j
- **Testing:** JUnit for unit testing
- **Database:** None (stateless system)

### Deployment
- **Containerization:** Podman
- **Instances:** Multiple isolated TrackSync instances running simultaneously for different operator/team configurations
- **Environment:** On-premises (military base in North Charleston, SC)

### Monitoring
- Internal monitoring tool built by a teammate, which also powered the frontend for users

### Performance
- **Production throughput:** ~350,000 tracks per minute (measured in production, not just a design requirement)

---

## Customer & Stakeholder Engagement

Vaughn made it clear to his PM that he wanted to be heavily involved in customer-facing and stakeholder-facing activities. As a result, he:

### Sprint Demos
- **Led multiple sprint demos** for audiences including:
  - Military operators (end users)
  - Subject matter experts (TAK and COP SMEs)
  - Program managers
  - Government contracting officers

### Requirement Discussions
- **Led and participated in requirement gathering sessions** with customers and stakeholders
- Translated technical constraints into business language
- Negotiated tradeoffs and proposed solutions when requirements conflicted with technical feasibility

### On-Site Customer Visits
- Occasionally visited the military base in North Charleston where customers were located
- **Activities during on-site visits:**
  - Plugged TrackSync into **real operational data** for testing
  - Gathered **direct feedback from potential users** (military operators)
  - Conducted **requirement gathering, training, and product demos**

### Communication Advocacy
- Advocated for **very open and frequent communication** across teams, especially when collaborating with engineers from other contracting companies on COMET
- Helped create a dynamic where multiple companies "felt like one team"

---

## Onboarding New Engineers

When the TrackSync team grew from 2 to 4 engineers at the start of the full contract (~June 2024), Vaughn took responsibility for **onboarding the two new junior engineers**.

### Onboarding Materials Created
- **System architecture diagrams**
- **Data flow visualizations**
- **COP/TAK domain knowledge explanations**
- **Development environment setup guides**
- **Presentations** to get new engineers up to speed quickly and efficiently

### Goal
Enable new engineers to contribute effectively to the project as quickly as possible, minimizing ramp-up time.

---

## COMET: Marine Task Management Web Application

### What COMET Does
COMET was an **end-to-end web application** designed to streamline Marine collection management workflows. Essentially, it was **like Monday.com, but specifically built for Marines and the tasks Marines had to do**.

### Vaughn's Role
- **Duration:** ~3-4 months (Feb/May 2024 – May/Jun 2024)
- **Primary work:** **Frontend development** using React and Material-UI (MUI)
- **Team scope:** Vaughn's team's role in COMET was **much smaller** compared to TrackSync
- **Clearance:** No security clearance required for COMET (unlike TrackSync full contract, which required Secret clearance)

### Collaboration with Other Contractors
- COMET involved **multiple contracting companies** from SRC and external partners
- Vaughn's team **collaborated with engineers from other companies**, integrating with their code, coordinating APIs, and dividing features
- **Within a few weeks, all teams felt like one unified team**
- Vaughn was a **strong advocate for very open and frequent communication**, facilitating:
  - **Shared Slack channels** for cross-company collaboration
  - **Joint standups** with all engineers from all companies

### Technical Stack (COMET)
- **Frontend:** React, Material-UI (MUI)
- **Backend:** (Vaughn's work was primarily frontend; backend details not recalled)

---

## TrackSync User Interface

While the "responsive user interfaces" mentioned on Vaughn's resume primarily refers to COMET, **TrackSync also had a frontend** that users interacted with.

### TrackSync Frontend Functionality
- **Monitoring and display:** Showed all tracks flowing through the system in real time
- **Track direction visualization:** Displayed whether tracks were moving from COP → TAK or TAK → COP
- **Built by teammate:** The frontend was built using an internal monitoring tool created by one of Vaughn's teammates

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

---

## Why Vaughn Left SRC for DraftKings (May 2025)

Vaughn left SRC for DraftKings for several reasons:
1. **Pay:** Better compensation
2. **Industry with higher ceiling:** Consumer tech vs. defense contracting
3. **Greater career trajectory:** More opportunities for growth and advancement
4. **Learning opportunities:** Most importantly, Vaughn felt he could learn more at DraftKings — exposure to larger-scale distributed systems, different technical challenges, and a faster-paced environment

---

## Additional Context

### Work Environment
- **Hybrid:** Office in North Charleston, SC; occasional on-site visits to the military base (also in North Charleston)
- **Clearance:** Secret clearance obtained during TrackSync full contract; expires ~June 2026

### Outcomes & Impact
- Most outcomes were **qualitative** rather than quantitative (no specific metrics like "reduced translation time by X%" available)
- **Key qualitative wins:**
  - Successfully translated ~350K tracks/min in production
  - Onboarded new engineers efficiently
  - Established "COP is King" as a program-level principle that prevented weeks of ambiguity
  - Built strong relationships with military operator SMEs
  - Delivered TrackSync OTA successfully, leading to a full-year contract

### Last Few Months at SRC
- **Polish and refinement:** Final months focused on polishing TrackSync for production stability
- **Preliminary V2 research:** Conducted early research for a potential TrackSync V2 contract (exploring next-generation features and improvements)

---

## Interview-Ready Stories

### Story 1: "COP is King" — Designing a Decision Framework
**Situation:** TrackSync ingested data from two sources (TAK and COP) that frequently conflicted, creating ambiguity for engineering, subcontractors, and customers.

**Task:** Find a way to resolve conflicts systematically without manual intervention or escalation.

**Action:** After observing repeated conflicts, Vaughn proposed the "COP is King" principle: COP is always the source of truth. He socialized it bottom-up (principal engineer → PM → SMEs → stakeholders), created a presentation for stakeholders, and incorporated feedback to define pragmatic exceptions.

**Result:** The principle was adopted program-wide, gave leadership a clear alignment point, and prevented weeks of ambiguity and rework.

**SE Relevance:** Demonstrates translating technical complexity into business-friendly principles, stakeholder communication, and cross-functional alignment.

---

### Story 2: Stateless Round-Trip Data Solution
**Situation:** COP had more precise track data than TAK. Original approach used a stateful lookup table to restore precision when tracks came back from TAK → COP, but the table grew quickly, caused performance issues, and broke in a stateless, multi-instance architecture.

**Task:** Find a way to preserve COP precision without external state.

**Action:** Vaughn embedded the extra COP data in a custom field within the TAK track itself, so it round-tripped cleanly without requiring a lookup table.

**Result:** Eliminated the stateful table, improved redundancy, improved efficiency, and worked seamlessly across multiple TrackSync instances.

**SE Relevance:** Shows systems thinking, identifying architectural flaws, and designing elegant solutions that balance technical constraints with operational needs.

---

### Story 3: SME Collaboration & Translation Logic
**Situation:** TrackSync had to translate data between two military systems (TAK and COP) with mismatched formats, missing fields, and completely different representations. "Correct" translation wasn't defined — it had to be discovered.

**Task:** Build translation logic that military operators would find effective and accurate.

**Action:** Vaughn worked directly with TAK and COP SMEs (military operators who used the systems daily), showing them data samples and asking, "How would this be represented in your system?" Iterated based on their feedback, negotiated tradeoffs, and refined the logic over time.

**Result:** Built translation logic that handled ~350K tracks/min in production and met operator expectations.

**SE Relevance:** Customer collaboration, requirement gathering, iterating based on user feedback, and bridging technical implementation with user needs.

---

### Story 4: Onboarding Engineers with Diagrams & Presentations
**Situation:** TrackSync team grew from 2 to 4 engineers at the start of the full contract. New engineers needed to ramp up quickly on a complex system with unique domain knowledge (COP/TAK).

**Task:** Get new engineers productive as fast as possible.

**Action:** Vaughn created system architecture diagrams, data flow visualizations, COP/TAK domain knowledge explanations, and development setup guides. Delivered presentations to walk new engineers through the system.

**Result:** New engineers ramped up efficiently and began contributing to the project.

**SE Relevance:** Knowledge transfer, technical communication, creating documentation and presentations for learning, and enabling team success.

---

## Summary

Vaughn's time at SRC was defined by **technical ownership of mission-critical translation logic**, **deep customer collaboration with military operators**, **cross-functional stakeholder engagement**, and **proactive problem-solving** that bridged engineering and program leadership. His work on TrackSync demonstrates both **technical depth** (handling 350K tracks/min, optimizing stateless architecture, building efficient data structures) and **Solutions Engineering strengths** (customer engagement, requirement negotiation, translating complexity for non-technical audiences, and driving alignment across teams). His role on COMET added frontend development experience and cross-company collaboration skills. Together, these experiences position Vaughn as someone who thrives at the intersection of engineering and people — exactly the profile of a strong Solutions Engineer candidate.
