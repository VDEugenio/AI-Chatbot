---
name: Skills Evidence Map
description: Direct evidence for "does Vaughn have experience with X?" — each sales skill, tool, and technology mapped to where he used it and how. Covers sales and pre-sales, AI/LLM tooling, orchestration, and infrastructure.
company: none
topics: [skills_evidence, sales_skills, presales, tools, frameworks, ai_ml, infrastructure, orchestration]
skills: [meddpicc, discovery, demos, proof_of_concept, prospecting, cold_outreach, full_cycle_sales, hubspot, apollo, airflow, kubernetes, kind, kubectl, helm, docker, rag, chromadb, bm25, hybrid_search, langchain, llm_evals, claude_api, prompt_engineering, openai_embeddings, fastapi, github_actions, aws]
story_types: [technical_depth, project]
related_files: [projects_index.md, technical_skills.md, feathery_role_overview.md, feathery_sales_approach.md, chatbot_rag_pipeline.md, draftkings_role_and_stack.md]
---

# Skills Evidence Map

Where and how Vaughn has used specific skills, tools, and technologies. Each entry names the project or job where the skill was applied.

## Sales & Pre-Sales

### Discovery & Qualification (MEDDPICC)
At Feathery, Vaughn runs discovery calls with insurance carriers and brokers and qualifies deals using MEDDPICC. It's especially central on the deals he has run end-to-end as the AE (two midsize brokers).

### Demos & Proofs of Concept
Building custom demos and proofs of concept is a core part of his day at Feathery. He has built demos from scratch in under a week several times, including full demos of COI and Employee Benefits workflows that weren't on the platform yet.

### Full-Cycle Deal Ownership (AE)
He has run deals as the Account Executive at Feathery, owning first conversations, discovery, demo build, and contract negotiation.

### Quota Attainment
He carries a quota at Feathery and is on pace for ~140% of a $750K ARR quota. The largest deal he has supported is over $350K.

### Prospecting, Business Development & Cold Outreach
He has the highest meetings-booked-per-conference rate among Feathery's SEs (about 7 meetings from a good conference; conferences include Guidewire Connections and NAMIC). During his career switch he sent 2,000+ cold outreach messages across LinkedIn, email, and phone, A/B testing his openers, and he built ICP Lab to rank prospects by predicted engagement.

### Implementation & Post-Sale Success
He has supported implementation and post-sale success for 5+ Feathery accounts worth several hundred thousand dollars each, and helped retain an at-risk customer after a platform regression.

### Technical Integrations in a Sales Context
He writes code and configures API integrations and connections to customers' AMS platforms and CRMs at Feathery.

### Sales Tools
HubSpot (CRM) and Apollo (prospecting and enrichment) at Feathery. Apollo, the Claude API, and his own ICP Lab for outbound prospecting.


## AI & LLM Engineering

### RAG (Retrieval-Augmented Generation)
Vaughn designed and built a production RAG system end-to-end: the AI Resume Chatbot (github.com/VDEugenio/AI-Chatbot). He owns every layer — knowledge-base authoring, header-aware chunking (1800-char chunks tuned through iteration), OpenAI embeddings, hybrid retrieval, metadata pre-filtering, query expansion, and Claude-based generation with hallucination guards. He chose RAG over fine-tuning deliberately and can articulate the trade-offs.

### ChromaDB
Vector store for the AI Resume Chatbot. Vaughn has run it in both embedded mode (file-based, bundled into the production Docker image on AWS App Runner) and client-server HTTP mode (standalone ChromaDB pod on Kubernetes, populated over the network). He manages collection lifecycle — full rebuilds, post-build verification, chunk-count auditing.

### Hybrid Search — BM25 + Vector + RRF
The chatbot's retrieval combines dense vector search with a BM25 keyword index, merged via Reciprocal Rank Fusion. Vaughn added BM25 after observing pure vector search miss exact-term queries (names, acronyms) — a concrete lesson in embedding limitations.

### LangChain
Used across the chatbot's ingestion and retrieval layers: RecursiveCharacterTextSplitter with custom markdown-header separators, document loaders, and the Chroma vectorstore integration.

### LLM Evaluation / Eval Harnesses
Vaughn built an automated eval harness for the chatbot: a curated question set with per-question keyword and source-citation checks, run against the live production API, an 80% accuracy gate in CI (GitHub Actions), timestamped result artifacts, and a baseline-comparison mode for detecting regressions precisely.

### Claude API & Prompt Engineering
Production integrations: the chatbot's answer generation (system prompts engineered for grounded, cited answers); the Job Application Tracker's email classification, where he chose Claude Haiku over larger models for cost efficiency and used prompt caching to cut per-email cost; and ICP Lab, where Claude Haiku parses job descriptions and buyer personas into structured LinkedIn title lists via forced tool calls.

### OpenAI Embeddings
text-embedding-3-small powers the chatbot's dense retrieval; Vaughn handles embedding-model/collection consistency between the ingestion pipeline and the backend.

### Performance & Power Optimization
Three flagship optimization stories across different domains: at SRC, trie-based ID validation and a parallelized translation pipeline pushing TrackSync to ~350K tracks/min; at DraftKings, Redis player-card caching and database query optimization for 500k+ peak users; and in VaughnKey, the power optimization — a deep-sleep-first architecture drawing ~10µA idle so a battery-powered device with a servo and BLE radio lasts 3–4 months per charge.

## Orchestration & Data Pipelines

### Apache Airflow
Vaughn runs a two-DAG Airflow deployment (Astronomer/Astro CLI) that keeps the chatbot's knowledge base synced with his GitHub activity. One DAG fetches repo metadata via the GitHub API, formats it into the corpus, and commits it back; a second handles human-in-the-loop enrichment — Claude generates gap-analysis questions, Vaughn answers via a Telegram-linked review UI, and the DAG commits the enriched context. Triggered by GitHub Actions with a debounce pattern; task communication via XCom.

## Infrastructure & Deployment

### Kubernetes (kind, kubectl)
Production exposure at DraftKings: DFS microservices ran on Kubernetes with seasonal scaling for NFL traffic peaks. Hands-on personal deployment: a local kind cluster running the chatbot's full stack — FastAPI backend and ChromaDB as separate Deployments with ClusterIP Services, a PersistentVolumeClaim for vector data, ConfigMap/Secret separation via envFrom, liveness/readiness probes, in-cluster DNS service discovery, and kubectl-driven operations (rollouts, rollbacks, scaling, port-forwarding, image side-loading into kind without a registry).

### Helm
At DraftKings, each microservice was deployed to Kubernetes via Helm charts — Vaughn worked with the chart-per-service deployment model as part of the team's release process.

### Docker
All personal projects are containerized: the chatbot backend's multi-stage Dockerfile (bakes the vector store into the image for App Runner), local docker-compose for development, and locally built images loaded into the kind cluster.

### AWS
DraftKings ran its DFS platform on AWS. Personally: the chatbot backend deploys to AWS App Runner via ECR, and the ADF Marketplace supports S3 as a pluggable storage backend (boto3, IAM instance-profile auth).

### PostgreSQL
Several personal-project backends run on PostgreSQL: the ADF Marketplace (SQLAlchemy, psycopg3), the Outreach Extension's tracking backend (psycopg2 with connection pooling, schema design for contacts/visit events), ICP Lab (least-privilege role with column-level grants on a shared Neon database), and Vinero (Neon, Alembic migrations).

### Chrome Extensions
The Outreach Extension is a Manifest V3 Chrome extension: popup UI, chrome.storage state persistence, tab inspection, and third-party API integration (Apollo.io contact enrichment) — built to instrument his LinkedIn job-search outreach with tracking links.

### GitHub Actions (CI/CD)
The chatbot repo runs a multi-workflow pipeline Vaughn designed: ingest-and-rebuild on knowledge-base changes with a gated production deploy, the eval harness on pushes and PRs with auto-posted PR summary comments, and a debounce-trigger workflow that batches Airflow DAG runs.

### MCP (Model Context Protocol) Servers
Vinero exposes an MCP server, so Claude and ChatGPT can query Vaughn's finances (transactions, budgets, net worth, card recommendations) through scoped OAuth tokens, with every write defaulting to a dry run.

### Plaid & Financial APIs
Vinero syncs bank transactions and investment holdings through Plaid, with encrypted access tokens and signed webhook verification.

### AI-Assisted Development (Claude Code)
Vaughn builds heavily with Claude Code. Vinero was built in about a month (90 commits over 13 active days) using Claude Code subagents, and he uses AI-assisted development at Feathery to build custom demos on short timelines.
