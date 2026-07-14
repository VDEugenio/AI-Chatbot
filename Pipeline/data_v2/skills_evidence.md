---
name: Skills Evidence Map
description: Direct evidence for "does Vaughn have experience with X?" — each tool/technology mapped to where he used it and how. Covers AI/LLM tooling, orchestration, and infrastructure.
company: none
topics: [skills_evidence, tools, frameworks, ai_ml, infrastructure, orchestration]
skills: [airflow, kubernetes, kind, kubectl, helm, docker, rag, chromadb, bm25, hybrid_search, langchain, llm_evals, claude_api, prompt_engineering, openai_embeddings, fastapi, github_actions, aws]
story_types: [technical_depth, project]
related_files: [projects_index.md, technical_skills.md, chatbot_rag_pipeline.md, draftkings_role_and_stack.md]
---

# Skills Evidence Map

Where and how Vaughn has used specific tools and technologies. Each entry names the project or job where the skill was applied.

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
Two production integrations: the chatbot's answer generation (system prompts engineered for grounded, cited answers), and the Job Application Tracker's email classification — where he chose Claude Haiku over larger models for cost efficiency and used prompt caching to cut per-email cost.

### OpenAI Embeddings
text-embedding-3-small powers the chatbot's dense retrieval; Vaughn handles embedding-model/collection consistency between the ingestion pipeline and the backend.

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
Two personal-project backends run on PostgreSQL: the ADF Marketplace (SQLAlchemy, psycopg3) and the Outreach Extension's tracking backend (psycopg2 with connection pooling, schema design for contacts/visit events). Deployed on Render and Railway respectively.

### Chrome Extensions
The Outreach Extension is a Manifest V3 Chrome extension: popup UI, chrome.storage state persistence, tab inspection, and third-party API integration (Apollo.io contact enrichment) — built to instrument his LinkedIn job-search outreach with tracking links.

### GitHub Actions (CI/CD)
The chatbot repo runs a multi-workflow pipeline Vaughn designed: ingest-and-rebuild on knowledge-base changes with a gated production deploy, the eval harness on pushes and PRs with auto-posted PR summary comments, and a debounce-trigger workflow that batches Airflow DAG runs.
