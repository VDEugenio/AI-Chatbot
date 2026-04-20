---
name: TrackSync Technical Stack
description: Backend, deployment, monitoring, and production-throughput details for TrackSync at SRC (Java/Spring Boot, Podman, in-memory queues, ~350K tracks/min).
company: src
topics: [tech_stack, containerization, in_memory_queues, performance, on_premises]
skills: [java, spring_boot, podman, log4j, junit, concurrent_linked_queue]
story_types: []
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
