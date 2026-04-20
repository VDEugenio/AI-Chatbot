---
name: TrackSync Architecture and Translation Logic Ownership
description: What TrackSync is (real-time middleware between TAK and COP military systems), internal architecture, stateless design, Vaughn's ownership of the translation logic, SME-driven workflow, and frontend monitoring UI.
company: src
topics: [military_systems, real_time_data, translation_logic, stateless_architecture, middleware, sme_collaboration]
skills: [java, spring_boot, system_architecture, real_time_processing]
story_types: [architecture_design, customer_collaboration, systems_thinking]
related_files: [src_tracksync_optimizations.md, src_cop_is_king.md]
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
- **Negotiating tradeoffs:** Initially had to push back or propose options when TAK and COP had incompatible representations, which led to the creation of the **"COP is King" principle** (see `src_cop_is_king.md`)

---

## TrackSync User Interface

While the "responsive user interfaces" mentioned on Vaughn's resume primarily refers to COMET, **TrackSync also had a frontend** that users interacted with.

### TrackSync Frontend Functionality
- **Monitoring and display:** Showed all tracks flowing through the system in real time
- **Track direction visualization:** Displayed whether tracks were moving from COP → TAK or TAK → COP
- **Built by teammate:** The frontend was built using an internal monitoring tool created by one of Vaughn's teammates
