---
name: AI Resume Chatbot — RAG Pipeline and Knowledge Base Design
description: How the knowledge base is structured (29 topic-scoped markdown files with YAML frontmatter), how chunking evolved from 500-char fragments to 1800-char header-aware sections, and how RRF hybrid retrieval with query expansion and company metadata filtering works.
company: personal
topics: [rag, retrieval, vector_search, bm25, hybrid_search, chunking, knowledge_base_design, embeddings, prompt_engineering]
skills: [rag_architecture, vector_databases, ChromaDB, OpenAI_embeddings, BM25, query_expansion, metadata_filtering, prompt_engineering]
story_types: [architecture_design, problem_solving, systems_thinking, technical_depth]
related_files: [chatbot_architecture.md, chatbot_challenges_decisions.md]
---

# RAG Pipeline and Knowledge Base Design

## The Core Problem RAG Solves Here

An LLM doesn't know anything about Vaughn. You could put his entire resume in the system prompt, but that approach has three problems:
1. A resume is a compressed summary — it lacks the depth to answer detailed follow-up questions
2. LLMs hallucinate details when forced to extrapolate beyond what they were given
3. Every chat message would re-send the full context, which is expensive and slow

RAG solves this by storing detailed knowledge externally and retrieving only the relevant pieces for each question. The LLM sees exactly what it needs to answer accurately, nothing more.

## Knowledge Base Structure

The knowledge base is **29 topic-scoped markdown files** in `Pipeline/data_v2/`. Each file covers one specific aspect of Vaughn's professional background:

### Organization by Domain
- **Profile** (4 files): overview, education, skills inventory, hobbies
- **DraftKings** (7 files): role/stack, architecture, performance, Ohtani project, feature flags, incident response, collaboration practices
- **SRC Inc** (8 files): role overview, TrackSync architecture, optimizations, COP-is-King framework, tech stack, customer engagement, COMET app, SE narratives/STAR stories
- **VaughnKey** (7 files): overview, hardware, software, UX, dev challenges, lessons, technical deep dive
- **Other** (3 files): AI chatbot project, internships (Swampfox, Marsh McLennan)

### YAML Frontmatter as Metadata
Every file has a YAML header with structured metadata:
```yaml
---
name: TrackSync Architecture and Translation Logic Ownership
company: src
topics: [military_systems, real_time_data, translation_logic]
skills: [java, spring_boot, system_architecture, real_time_processing]
story_types: [architecture_design, customer_collaboration]
related_files: [src_tracksync_optimizations.md, src_cop_is_king.md]
---
```

This frontmatter is parsed during ingestion and stored as ChromaDB metadata on every chunk produced from that file — enabling metadata-filtered retrieval at query time.

## Chunking Strategy — Evolution

### V1: Fixed-Size Chunking (the mistake)
The original pipeline used 500-character chunks (~100 tokens) with 50-character overlap.

**The problem:** A complete STAR story — like the DraftKings "Early Start Bug" incident narrative — spans ~2,400 characters. At 500-char chunks, it became 5 separate fragments. Each fragment lacked enough context to be useful independently. When retrieved, the LLM would get disconnected pieces of a story rather than the coherent narrative.

Result: answers felt shallow and incomplete even when the right content existed.

### V2: Header-Aware Chunking (current)
The current pipeline splits on markdown section boundaries first (`## / ###`), then falls back to paragraph/line/word splits only when sections exceed the size limit.

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1800,   # ~450 tokens — keeps full sections intact
    chunk_overlap=200,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "],
)
```

**Result:** 99 rich chunks instead of 137 small ones. A complete STAR story or architecture explanation now fits in 1-2 chunks. The LLM sees coherent context, not fragments.

## Retrieval Pipeline

### Step 1: Query Expansion
Before embedding, the query is enriched with synonym/entity groups to bridge vocabulary gaps between how questions are phrased and how content is written:

```python
# Example: "Tell me about a time you optimized something"
# Triggers expansion group → appends:
# "optimized performance faster improved streamlined reduced enhanced"
```

Company-specific groups boost exact entity recall in BM25:
- Trigger: "src", "tracksync", "military" → appends TrackSync, COMET, TAK, COP, Java, Spring Boot keywords
- Trigger: "draftkings", "dfs", "ohtani" → appends DraftKings, .NET, Orleans, Redis, RabbitMQ keywords

### Step 2: Metadata Pre-Filtering
If the query mentions a specific employer or project, the vector search is pre-filtered to matching chunks before any similarity computation:

```python
# "What did you build at SRC?" → filter: {"company": "src"}
# "Tell me about your personal projects" → filter: {"company": "personal"}
```

Pre-filtering is fast (no extra LLM call) and dramatically improves precision for role-specific questions by eliminating irrelevant documents before the search runs.

### Step 3: RRF Hybrid Retrieval
Two retrievers run on the same expanded query:

**Vector retrieval (dense)** — embeds the query with OpenAI `text-embedding-3-small` and searches ChromaDB by cosine similarity. Captures semantic meaning: "distributed systems" → TrackSync, even if "distributed" isn't literally in the document.

**BM25 retrieval (sparse)** — keyword-based search using an in-memory BM25Okapi index built from ChromaDB at startup. Captures exact term matches: "TrackSync", "Ohtani", "Orleans", "C#". These proper nouns and tech names are exactly what embedding models often miss.

**Reciprocal Rank Fusion (RRF)** fuses both result lists without requiring score normalization:
```
RRF_score(chunk) = 1/(60 + vector_rank) + 1/(60 + bm25_rank)
```

A chunk appearing at rank 1 in both lists scores higher than one at rank 1 in only one. The top K fused results go to Claude.

### Step 4: Prompt Assembly
Retrieved chunks are injected into the user message with source attribution:
```
[source: src_tracksync_architecture.md#1 | TrackSync Architecture and Translation Logic Ownership]
## TrackSync: Real-Time Military Track Exchange Middleware
...
```

### Step 5: Grounded Generation
Claude receives a system prompt with strict factuality rules:
- Only use information from the provided context
- Never infer or add details not explicitly present
- State dates, company names, and technologies exactly as they appear
- If context is insufficient, say so rather than guessing

Temperature is set to 0.0 for maximum determinism on factual responses.

## Debug Endpoints

The backend exposes two debug endpoints used during development to inspect retrieval quality without guessing:

- **`POST /api/debug/retrieve`** — runs the full retrieval pipeline and returns every chunk with its score, filename, company metadata, and preview — no LLM call
- **`POST /api/debug/compare`** — runs vector, BM25, and BM25+rerank side-by-side for the same query so you can see exactly which approach surfaces what
