---
name: AI Resume Chatbot & Portfolio Website — Overview and Motivation
description: Why Vaughn built an AI-powered chatbot as his personal website, what problem it solves, and why this project is interesting both as a job-search tool and as an engineering demonstration.
company: personal
topics: [ai_ml, chatbot, personal_website, interactive_resume, rag, product_pitch]
skills: [rag_architecture, prompt_engineering, system_design, product_thinking]
story_types: [product_pitch, problem_solving, engineering_rationale]
related_files: [chatbot_architecture.md, chatbot_rag_pipeline.md, chatbot_challenges_decisions.md]
---

# AI Resume Chatbot & Portfolio Website

**GitHub:** https://github.com/VDEugenio/AI-Chatbot

## What This Project Is

Vaughn built a personal website centered around an AI-powered chatbot that acts as an interactive resume. Instead of sending recruiters and hiring managers a static PDF, Vaughn's site lets them have a real conversation with an AI that knows everything about his professional background — his roles, projects, technical skills, engineering decisions, and career goals.

The site has two main parts:
- **The chatbot** — a RAG-powered AI assistant that answers questions about Vaughn's experience in natural language
- **The portfolio** — a structured sidebar/drawer showing his work experience timeline, personal projects (see `projects_index.md` for the full list), skills and tech stack, and contact/social links

## The Dual Motivation

This project was built with two equally important goals:

### 1. Stand Out in the Job Search
A static resume is easy to ignore. An interactive chatbot that a recruiter can actually talk to is memorable. The goal was to create something that demonstrates both Vaughn's technical depth and his ability to build products that solve real problems for real users — in this case, the "user" being the recruiter trying to evaluate him.

Rather than hoping a recruiter reads every bullet point on a PDF, Vaughn built a system where they can ask specific questions: "What did you do at SRC?", "Has he worked with distributed systems?", "What's his most complex project?" — and get accurate, detailed answers instantly.

### 2. Learn RAG Engineering by Building It
The chatbot is also a hands-on learning project in retrieval-augmented generation (RAG) — a production AI pattern that Vaughn was deeply interested in but hadn't built from scratch. Building it himself meant designing the full stack: how to organize and chunk knowledge, how to embed and retrieve it, how to prompt an LLM to stay grounded in facts, and how to deploy it reliably.

The project forced Vaughn to confront real RAG problems — not toy examples — including retrieval inconsistency, chunking strategy, hallucination prevention, and hybrid search. These are the same problems production AI teams deal with, and solving them in a personal project gave Vaughn genuine expertise he wouldn't have gotten any other way.

## Why It's Interesting as an Engineering Project

Most "AI chatbot" projects are thin wrappers around an LLM API. This project is different because:

1. **The knowledge base is structured deliberately** — a growing corpus of ~40 topic-scoped markdown files with YAML metadata, not a raw PDF dump. Each file covers a specific aspect of Vaughn's experience (a role, a project, an architectural decision, an engineering challenge) with enough depth to answer detailed follow-up questions.

2. **Retrieval is a solved problem, not an afterthought** — The system uses hybrid search (dense vector + BM25 keyword retrieval fused via Reciprocal Rank Fusion), query expansion, and company-level metadata pre-filtering. These aren't random features — each one addresses a specific retrieval failure mode Vaughn observed.

3. **Accuracy matters here** — Unlike a general-purpose chatbot, this one is specifically representing Vaughn to potential employers. A hallucination isn't just a bad AI response — it's a misrepresentation of his experience. Getting grounding and factuality right was a primary engineering constraint, not an afterthought.

4. **It's a real production system** — Docker, AWS App Runner, a React frontend, FastAPI backend, debug endpoints, logging, config management. Not a Jupyter notebook.

## Current Status

The project is live in production at https://vaughneugenio.com and actively developed. The chatbot knowledge base, retrieval pipeline, and frontend portfolio are all built and functional.
