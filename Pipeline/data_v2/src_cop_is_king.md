---
name: '"COP is King" Decision Framework'
description: How Vaughn proposed, socialized bottom-up, and drove program-wide adoption of the "COP is King" principle to resolve TAK/COP data conflicts — a quintessential Solutions-Engineering win translating technical complexity into a business-aligned decision framework.
company: src
topics: [decision_framework, conflict_resolution, stakeholder_alignment, program_leadership, technical_communication]
skills: [stakeholder_communication, technical_liaison, program_level_thinking, presentation]
story_types: [architecture_design, stakeholder_communication, cross_functional, customer_collaboration, technical_leadership, product_pitch]
related_files: [src_tracksync_architecture.md, src_customer_engagement_onboarding.md, src_se_narratives_and_stories.md]
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
