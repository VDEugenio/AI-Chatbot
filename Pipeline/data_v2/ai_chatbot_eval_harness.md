---
name: AI Chatbot Eval & Test Harness
description: Automated evaluation framework for the RAG chatbot — 23 question test set, CI/CD integration, and pipeline smoke tests
company: personal
topics: [ai_ml, chatbot, testing, ci_cd, eval_harness]
skills: [test_automation, ci_cd, rag_evaluation, quality_assurance]
story_types: [product_pitch, problem_solving, technical_depth]
related_files: [ai_chatbot_project.md, chatbot_overview.md]
---

# AI Chatbot Eval & Test Harness

The AI chatbot project includes a comprehensive automated evaluation harness designed to ensure the RAG pipeline consistently retrieves relevant documents and generates accurate answers. Rather than relying on manual spot-checks, the system is tested end-to-end on every code change.

## The Problem the Eval Harness Solves

A RAG system has multiple failure modes that are hard to catch manually: embeddings may drift, chunking strategy changes can fragment important context, retrieval thresholds may be too loose or too strict, and prompt changes can silently degrade answer quality. Without automated coverage, regressions only surface when a real user notices a bad answer — by which point the system is already in production.

The eval harness treats the chatbot like any other software system: changes that break observable behavior fail the build before they can ship.

## Eval Script (`tests/run_eval.py`)

The core evaluation script runs 23 curated test questions against the live backend API and verifies that each answer meets quality criteria:

- Each question defines a set of **required keywords** that must appear in the answer (case-insensitive substring match) and a list of **expected source documents** that should be cited in the response
- Response timing is tracked: a warning is emitted if any response exceeds 15 seconds, and individual requests time out at 30 seconds
- An **80% accuracy threshold** is applied as the pass/fail threshold for CI decisions — the test run fails if fewer than 80% of questions pass their keyword and source checks
- Results are written to **timestamped JSON files** in `tests/results/` so every run is auditable
- The script supports **filtering** by topic category or specific question ID for targeted debugging
- A **baseline comparison mode** lets a known-good run be saved and future runs diffed against it — this makes it easy to spot regressions precisely rather than just seeing an overall score drop

## Question Set (`tests/eval_questions.json`)

The 23 test questions are organized into 6 topic categories:

- **efficiency** — questions about reducing overhead, latency improvements, and system optimization
- **technical** — architecture decisions, technology choices, and implementation details
- **projects** — questions about specific projects Vaughn has built or contributed to
- **collaboration** — cross-functional work, stakeholder communication, and team dynamics
- **career** — background, motivations, and professional trajectory
- **ui_chip** — the exact questions shown as suggestion chips in the chatbot UI itself (these are tested verbatim to ensure the most visible user-facing prompts always produce good answers)

The questions cover all major domains in Vaughn's experience:

- **DraftKings**: Orleans actor model, RabbitMQ, Redis, the Consumer Transactions platform
- **SRC / TrackSync**: Java/Spring Boot services, COMET, military domain work
- **VaughnKey smartlock**: ESP32, BLE protocol, hardware challenges, power bank modification
- **AI chatbot itself**: ChromaDB, embeddings, FastAPI backend, RAG pipeline design

Each question in the JSON includes a `question` string, a `category` string, a `keywords` list (minimum required terms), and a `sources` list (expected document filenames).

## CI/CD Integration (`.github/workflows/eval.yml`)

The evaluation workflow runs automatically on every push to `main` and on all pull requests. This ensures that no RAG regression can reach production without being caught:

- The workflow calls the eval script against the **production API URL**, configurable via the `CHAT_API_URL` environment variable — so it always tests the real deployed system, not a mock
- Full JSON results are uploaded as a **GitHub Actions artifact** named `eval-results-{commit-sha}`, making every run's raw output permanently available for audit or debugging
- A **PR comment is automatically posted** with a markdown summary table showing: overall pass rate, average response time across all 23 questions, per-topic accuracy breakdown, and a list of any failed questions with the specific keywords or sources that were missing
- **CI fails if accuracy drops below 80%**, blocking merges that would degrade the user experience

## Pipeline Smoke Test (`Pipeline/ingest.py`)

After every ChromaDB index rebuild, a `test_query()` function runs two sample queries — "What experience does Vaughn have?" and "Tell me about TrackSync at SRC" — against the freshly built vector store. It prints snippet previews of the top-3 retrieved chunks for each query, confirming that vector search is operational and that the expected content surfaces correctly before the pipeline exits.

This catch is intentionally lightweight: it doesn't enforce pass/fail, but it makes a broken rebuild visible immediately rather than letting a silent failure propagate to a deployed backend.

## What This Demonstrates

The eval harness reflects Vaughn's commitment to building observable, maintainable systems rather than shipping and hoping. Key skills demonstrated:

- **Test automation at the application layer** — end-to-end tests that exercise the full stack (vector retrieval, LLM generation, API response) rather than just unit tests
- **CI/CD pipeline design** — GitHub Actions workflow that integrates quality gates into the development process so regressions are caught automatically
- **RAG-specific evaluation thinking** — understanding that RAG systems need both retrieval quality checks (are the right sources cited?) and generation quality checks (are the right keywords present?), and that these are distinct failure modes
- **Developer experience investment** — baseline comparison, per-topic breakdowns, and PR comment summaries make it fast to understand what broke and why, not just whether something broke
- **Building in production awareness** — testing against the live production API URL (not a local mock) ensures the eval reflects real deployed behavior
