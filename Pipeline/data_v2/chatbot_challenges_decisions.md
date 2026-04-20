---
name: AI Resume Chatbot — Engineering Challenges and Key Decisions
description: The two hardest problems Vaughn solved (retrieval quality and chunking strategy), why he chose RAG over fine-tuning, hybrid BM25+vector over vector-only, and Claude over other LLMs.
company: personal
topics: [engineering_decisions, problem_solving, rag, retrieval, technical_tradeoffs, ai_ml]
skills: [rag_architecture, technical_judgment, system_design, problem_analysis]
story_types: [problem_solving, technical_depth, architecture_design, engineering_rationale]
related_files: [chatbot_rag_pipeline.md, chatbot_overview.md, chatbot_lessons_status.md]
---

# Engineering Challenges and Key Decisions

## Hardest Problem 1: Retrieval Quality

The first version of the chatbot retrieved the wrong information constantly. A question like "Tell me about your SRC experience" would surface DraftKings chunks. A question about the Ohtani project would return generic profile content. The chatbot would either say something wrong or give a vague non-answer.

The root cause was that vector search alone isn't reliable for a resume chatbot:

1. **Vocabulary mismatch** — questions are phrased differently than the source documents. "Tell me about real-time systems" doesn't embed close to "350,000 tracks per minute" even though they're about the same thing.

2. **Proper noun blindness** — embedding models struggle with proper nouns like "TrackSync", "Ohtani", "Abacus", "Orleans". These terms are central to resume content but semantically opaque to dense embeddings.

3. **No signal about which employer was asked about** — a question about SRC would retrieve the highest-scoring chunks globally, which often weren't SRC chunks at all.

**How it was solved:**

- **Query expansion** — appends synonym/entity lists to the query before embedding, bridging the vocabulary gap
- **Company metadata pre-filtering** — detects the employer or project being asked about and restricts the search space before retrieval runs
- **RRF hybrid search** — BM25 catches exact proper noun matches that vector search misses; fusion combines both signals

The combination of all three brought retrieval from unreliable to consistent.

## Hardest Problem 2: Chunking Strategy

The original chunking used a fixed 500-character limit — a common default in RAG tutorials. It produced 137 small chunks that each lacked context.

The core issue: resume content isn't structured like a FAQ. It's narrative. A STAR story — situation, task, action, result — needs to be read as a unit. When the "Early Start Bug" incident story was split into 5 fragments across five chunk boundaries, each fragment independently looked like the right result for different queries, but none contained the full story. The LLM would get fragment #3 of 5 and give an incomplete answer.

**The realization:** the chunking problem isn't really about chunk size — it's about respecting the semantic structure of the source documents. The markdown files are already organized into sections (`## Major Section`, `### Sub-section`). The splitter should respect those boundaries, not cut through them.

**The fix:** switched to header-aware recursive splitting with a 1800-character limit. The splitter tries `\n## ` splits first, then `\n### `, then paragraphs, then lines. An entire `## ` section stays together as one chunk whenever it fits. This brought the chunk count from 137 to 99 — fewer, richer chunks that each contain a complete thought.

## Key Decision: RAG vs Fine-Tuning

**Why not fine-tune a model on Vaughn's resume?**

Fine-tuning trains knowledge into model weights — it's permanent until you retrain. For a resume chatbot, this is the wrong tradeoff:
- **Vaughn's resume changes** — new jobs, new projects, new skills. With RAG, updating the knowledge base is `python ingest.py`. With fine-tuning, it's a full retraining run.
- **Hallucination risk is higher** — fine-tuned models confidently confabulate information they learned imperfectly during training. RAG grounds every response in retrieved text the LLM can actually see.
- **Interpretability** — with RAG, you can inspect exactly which chunks were retrieved for any response. With fine-tuning, there's no way to know what the model is drawing on.

RAG also lets Vaughn use state-of-the-art frontier models (Claude, GPT-4) rather than a fine-tuned smaller model.

## Key Decision: Hybrid BM25 + Vector Search

**Why not just vector search?**

Vector search (dense retrieval) is semantically powerful but has a specific blind spot: proper nouns and technical terms that appear infrequently in training data don't embed reliably. "TrackSync", "BM25Okapi", "RabbitMQ", "Ohtani" — these are either rare or domain-specific enough that their embedding vectors don't reliably cluster with semantically related content.

BM25 (a classic keyword search algorithm) handles these exactly: it scores documents by exact term overlap with the query. When someone asks about "the Ohtani project", BM25 will find the Ohtani chunks because "Ohtani" is literally there.

The combination via Reciprocal Rank Fusion is better than either alone:
- Vector retrieval handles semantics and paraphrasing
- BM25 handles exact names, jargon, and acronyms
- RRF fuses them using only rank position, so mismatched score scales between the two retrievers don't matter

Implementing hybrid search required building a BM25 index in-memory at backend startup (from the same ChromaDB data), wiring both retrievers to run on each query, and implementing the RRF fusion logic. Not a simple config change — but the improvement in retrieval accuracy was immediately visible.

## Key Decision: Claude over GPT for Generation

Both were strong candidates. Claude was chosen for two reasons:

1. **Instruction-following fidelity** — the system prompt imposes strict factuality rules ("never infer details not in context", "cite sources", "say you don't know rather than guessing"). Claude follows these constraints more reliably than alternatives, which matters here because a hallucinated answer is a direct misrepresentation of Vaughn's experience.

2. **Context window** — Claude's large context window means the full retrieved context (up to 8 chunks × ~450 tokens each) fits comfortably alongside conversation history and system instructions without truncation pressure.
