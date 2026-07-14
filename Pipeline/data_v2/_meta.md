# data_v2 — Index

> **Note:** This file is a human-maintained index of the directory. It is excluded from ingestion (underscore-prefixed files are skipped by `ingest.py`).

Topic-scoped RAG corpus for Vaughn Eugenio's professional context. Every file carries YAML frontmatter (`company`, `topics`, `skills`, `story_types`, optional `related_files`). See `Pipeline/data_backup/` for the four original pre-restructure source files.

---

## Profile

- **profile_overview.md** — Overview, contact info, career focus, employment history, personal projects table, and synthesized professional strengths across all roles. (tags: career_transition, solutions_engineering, cross_functional)
- **technical_skills.md** — Full inventory of languages, frameworks, AI/LLM tooling, infrastructure, data/messaging, frontend, and tooling skills. (tags: tech_stack, ai_ml)
- **education.md** — University of South Carolina B.S. Computer Science credentials and honors. (tags: education)
- **hobbies_and_interests.md** — Brazilian Jiu-Jitsu, golf, and cooking. (tags: personal_interests)
- **swampfox_internship.md** — Summer 2022 internship: SFValid debugging tool and automated CCXML/VXML call workflows. (tags: internal_tooling, call_center, agile)
- **marsh_mclennan_internship.md** — Summer 2021 internship: Python/Pandas data pipelines, K-Means/BIRCH clustering, R→Python migration. (tags: data_pipelines, machine_learning)

## DraftKings (May 2025 – Feb 2026)

- **draftkings_role_and_stack.md** — Role overview, DFS product context, team structure, and full C#/.NET/Orleans/AWS/K8s/RabbitMQ/Redis stack. (tags: daily_fantasy_sports, distributed_systems, tech_stack)
- **draftkings_architecture.md** — 15+ microservices: Abacus, Titan, Scoreboard, Scores; RabbitMQ inter-service pattern. (tags: microservices, event_driven)
- **draftkings_performance_scale.md** — 500k+ peak users, Redis player-card caching, DB query optimization, seasonal K8s scaling. (tags: performance_optimization, caching, kubernetes_scaling)
- **draftkings_ohtani_project.md** — Cross-functional dual-Draftable solution for Shohei Ohtani's pitcher+hitter edge case; solution pitched across eng, product, sports intelligence, DB teams. (tags: product_pitch, cross_functional, edge_cases)
- **draftkings_feature_flags.md** — Feature flag strategy: safe rollouts, Redis toggles, emergency kill switches. (tags: feature_flags, safe_rollouts)
- **draftkings_incident_response.md** — On-call rotation + full early-start validation bug narrative: 25-minute user mitigation, root cause, fix, logging improvements. (tags: on_call, incident_response, root_cause_analysis)
- **draftkings_practices_collaboration.md** — Code review culture, DI scoping, interface usage, cross-functional collaboration, career direction, and scale metrics. (tags: code_review, cross_functional, career_direction)

## SRC (Oct 2023 – May 2025)

- **src_role_overview.md** — Role, team, timeline (OTA → COMET → full contract), Secret clearance, outcomes, and departure rationale. (tags: defense_contractor, timeline, security_clearance)
- **src_tracksync_architecture.md** — TrackSync middleware between TAK (field) and COP (command) military systems; stateless design; Vaughn's ownership of translation logic; SME workflow; monitoring UI. (tags: military_systems, real_time_data, translation_logic)
- **src_tracksync_optimizations.md** — Three core optimizations: tree-based ID validation (trie), parallelized translation for 350K tracks/min, embedding COP precision in TAK custom fields to remove a stateful lookup table. (tags: performance_optimization, data_structures, stateless_architecture)
- **src_cop_is_king.md** — "COP is King" decision framework: problem, bottom-up socialization, program-wide adoption, and why it's a quintessential Solutions-Engineering story. (tags: decision_framework, stakeholder_alignment, technical_communication)
- **src_tech_stack.md** — Java/Spring Boot, Podman, in-memory queues, log4j, JUnit; ~350K tracks/min production throughput. (tags: tech_stack, containerization)
- **src_customer_engagement_onboarding.md** — Sprint demos, requirement gathering, on-site base visits, plus onboarding new engineers with diagrams and domain-knowledge presentations. (tags: customer_engagement, on_site_visits, onboarding)
- **src_comet.md** — COMET Marine task-management web app (Monday.com-like); frontend React/MUI work; cross-company collaboration. (tags: web_application, cross_company_collaboration, frontend)
- **src_se_narratives_and_stories.md** — Five SE-positioning narratives mapping SRC work to Solutions Engineering competencies; full stories live in the referenced source files. (tags: solutions_engineering, interview_prep, technical_communication)

## VaughnKey (personal smart-lock project)

- **smartlock_overview.md** — Project overview, problem (rental + no permanent install), evolution timeline (WiFi ARP and handle-turn sensing abandoned; capacitive touch + BLE won), and tunable firmware parameters. (tags: iot, embedded_systems, requirements_evolution)
- **smartlock_hardware.md** — ESP32, capacitive peephole sensor, DS-S012 servo, modified power bank, BLE beacon, 3D-printed housing, deep-sleep power architecture, servo mechanical linkage, command-strip installation. (tags: hardware_design, deep_sleep, servo, mechanical_linkage)
- **smartlock_software.md** — Code-level execution flow (wake → touch measurement → action dispatch → servo/BLE → sleep) and BLE authentication (current name-based, planned UUID-based with nRF51822, security tradeoffs). (tags: firmware, execution_flow, authentication, ios_background_ble)
- **smartlock_ux.md** — Touch-duration gestures, physical interaction flows for arriving/leaving, and asymmetric auth rationale (unlock requires BLE, lock does not). (tags: user_experience, interaction_design, touch_sensing)
- **smartlock_dev_and_challenges.md** — Dev tools, project file layout, utility sketches, required libraries, and five engineering challenges overcome. (tags: development_tools, challenges, debugging)
- **smartlock_lessons_future_status.md** — Five design-philosophy lessons, remaining work and future enhancements, edge cases, current status, and why the project demonstrates engineering competence. (tags: lessons_learned, future_work, engineering_competence)
- **smartlock_technical_deepdive.md** — Quantitative power-budget analysis, why capacitive touch beat every alternative, and why BLE beat WiFi on power/range/security/complexity. (tags: power_budget, capacitive_touch, protocol_comparison)

## Chatbot & Job Tracker (personal projects)

- **chatbot_overview.md** — Why Vaughn built the chatbot (dual motivation: recruiter tool + RAG learning), what the portfolio site contains, why this project is interesting. (tags: ai_ml, rag, personal_website, product_pitch)
- **chatbot_architecture.md** — Full system architecture: FastAPI backend, React frontend, ChromaDB, OpenAI embeddings, Claude, Docker, AWS App Runner. (tags: system_architecture, backend, deployment)
- **chatbot_rag_pipeline.md** — Knowledge base structure (~40 markdown files + YAML metadata), chunking evolution (500→1800 chars), RRF hybrid retrieval, query expansion, company filtering. (tags: rag, retrieval, hybrid_search, chunking)
- **chatbot_challenges_decisions.md** — Two hardest problems (retrieval quality, chunking), plus why RAG over fine-tuning, BM25+vector over vector-only, and Claude over GPT. (tags: engineering_decisions, problem_solving)
- **chatbot_lessons_status.md** — Five lessons learned building a production RAG system, current status, and what's coming next. (tags: lessons_learned, current_status)
- **ai_chatbot_eval_harness.md** — Automated eval framework: 23-question test set with keyword and source-citation checks, 80% accuracy gate in CI, baseline-comparison mode, pipeline smoke tests. (tags: eval_harness, testing, ci_cd)
- **job_tracker_overview.md** — Job Application Tracker: Gmail OAuth + Claude Haiku email classification, built in a few hours; replaces manual spreadsheet with an automated React dashboard. (tags: automation, ai_ml, rapid_development, personal_project)
- **job_tracker_technical.md** — Tech stack (FastAPI, SQLite, Gmail API, Claude Haiku, React), prompt caching, CSRF-safe OAuth, status rank enforcement, deduplication logic, and security decisions. (tags: system_architecture, oauth2, prompt_caching, security)
- **outreach_extension.md** — Chrome extension for LinkedIn outreach: Apollo.io contact enrichment, templated messages, unique tracking links with Telegram click notifications; FastAPI + PostgreSQL backend on Railway. (tags: chrome_extension, job_search, api_integration, personal_project)

## GitHub-generated (auto-synced by the Airflow DAG)

- **github_VDEugenio_AI_Chatbot.md** — Repo summary for AI-Chatbot: the production RAG backend (FastAPI, ChromaDB, OpenAI embeddings, Claude). (tags: github, personal_projects)
- **github_VDEugenio_Job_Application_Tracker.md** — Repo summary for Job-Application-Tracker: Gmail scraping + Claude classification dashboard. (tags: github, personal_projects)
- **github_VDEugenio_VaughnKey.md** — Repo summary for VaughnKey: recent activity and file structure, including tap-detection Telegram firmware. (tags: github, personal_projects)
- **github_VDEugenio_adf_marketplace.md** — Repo summary for adf-marketplace: marketplace for Rawl-agent .adf files ("Hugging Face, but for Rawl agents"). (tags: github, personal_projects)

## Aggregation

- **projects_index.md** — Canonical list of ALL of Vaughn's personal projects with tech, repo links, and status. (tags: personal_projects, portfolio)
- **skills_evidence.md** — Skill→evidence map: each tool/technology (RAG, ChromaDB, Airflow, Kubernetes/kind, Helm, Docker, AWS, GitHub Actions, …) mapped to where and how Vaughn used it. (tags: skills_evidence, ai_ml, infrastructure)

---

**Total:** 42 files (6 profile + 7 DraftKings + 8 SRC + 7 VaughnKey + 8 chatbot/job tracker + 4 GitHub-generated + 2 aggregation) + this index.

**Originals preserved in:** `Pipeline/data_backup/`.
