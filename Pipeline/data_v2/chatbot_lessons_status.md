---
name: AI Resume Chatbot — Lessons Learned and Current Status
description: What Vaughn learned building a production RAG system from scratch, what the current state of the project is, and what's coming next.
company: personal
topics: [lessons_learned, rag, iteration, engineering_growth, current_status, future_work]
skills: [rag_architecture, system_design, problem_analysis, engineering_judgment]
story_types: [lessons_learned, engineering_rationale, technical_depth]
related_files: [chatbot_challenges_decisions.md, chatbot_overview.md, chatbot_rag_pipeline.md]
---

# Lessons Learned and Current Status

## What Building This Taught Vaughn About RAG

### 1. Chunking is the most underrated problem in RAG

Every RAG tutorial focuses on embeddings and LLM prompting. Almost none spend serious time on chunking. But chunking is actually the highest-leverage decision you make: a bad chunking strategy means bad retrieval no matter how good your embedding model or how sophisticated your retrieval algorithm.

The lesson: chunk size should match the unit of meaning in your content, not a number from a tutorial. For narrative resume content, that unit is a markdown section. For a FAQ, it might be a single Q&A pair. For a legal document, it might be a clause.

### 2. Retrieval failures are hard to diagnose without instrumentation

When the chatbot gives a wrong answer, the cause could be anywhere: wrong chunks retrieved, correct chunks retrieved but not enough context, correct context but bad prompting, or hallucination despite good context. Without visibility into what was retrieved, debugging is guesswork.

Building the `/api/debug/retrieve` and `/api/debug/compare` endpoints early was one of the best decisions made on this project. They made every retrieval failure diagnosable — you could see exactly which chunks were returned, their scores, and which retrieval mode surfaced them.

### 3. Metadata is not optional — it's the multiplier

Storing `company`, `topics`, and `skills` as ChromaDB metadata turned a flat list of chunks into a structured, filterable knowledge base. A question about SRC can now restrict its search to SRC chunks before any similarity computation runs. This is faster, more precise, and prevents cross-contamination between employers.

The investment was: one YAML header per file + frontmatter parsing in the ingest pipeline. The payoff was: company-scoped filtering, future skill-based filtering, and richer source attribution in responses.

### 4. Hybrid search is worth the extra complexity

Adding BM25 alongside vector search required: building a BM25 index at startup, implementing RRF fusion, and testing that both retrievers were contributing meaningfully. That's real engineering work.

But proper nouns — "TrackSync", "Ohtani", "Orleans", "COMET" — are central to resume content, and they're exactly what dense embedding models handle poorly. BM25 fills that gap. The combination consistently outperforms either retrieval mode alone, especially for specific entity queries.

### 5. The system prompt is a contract, not a suggestion

Early versions of the system prompt said something like "answer accurately and don't make things up." Claude would still sometimes extrapolate or soften vague context into confident-sounding statements.

The current system prompt is explicit and enumerated: exact instructions, no wiggle room, zero-temperature output. The lesson: for factual grounding in a domain where correctness matters (someone's employment history), a vague system prompt is not enough. You need explicit rules.

## What Demonstrating This Project Shows

This project demonstrates several things that are hard to show on a resume:

- **Production RAG engineering** — not a tutorial, not a hackathon project. A full pipeline with instrumented retrieval, hybrid search, metadata filtering, and grounded generation.
- **End-to-end product thinking** — designed for a real user (recruiters/hiring managers) with a clear problem being solved
- **Iteration based on real failure modes** — the chunking and retrieval decisions came from observing actual failures, not from reading papers
- **Full-stack ownership** — frontend (React/TypeScript), backend (FastAPI/Python), data pipeline (ChromaDB/OpenAI), deployment (Docker/AWS)

## Current Status and What's Next

**Current state:** Fully functional locally. The chatbot, portfolio frontend, and RAG pipeline are all working. Awaiting deployment to a custom domain.

**Coming next:**
- Live deployment on personal domain (publicly accessible to recruiters)
- Portfolio drawer UI completion (work experience, projects, skills, contacts fully populated)
- Potential addition of eval framework to track retrieval quality over time as knowledge base grows
- Possible reranking improvements using cross-encoder models if retrieval quality plateaus
