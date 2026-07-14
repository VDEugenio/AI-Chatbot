---
name: Personal Projects Index
description: Canonical list of ALL of Vaughn's personal projects with one-line summaries, tech, repo links, and status. The authoritative answer to "what personal projects has Vaughn worked on?"
company: personal
topics: [personal_projects, portfolio, side_projects, github]
skills: [full_stack, ai_ml, embedded_systems, cloud_deployment]
story_types: [project]
related_files: [chatbot_overview.md, smartlock_overview.md, job_tracker_overview.md, skills_evidence.md]
---

# Personal Projects — Complete Index

Vaughn has built **five personal projects**, all with public GitHub repositories. This is the complete list; each has dedicated files with full detail.

### 1. AI Resume Chatbot & Portfolio Website
**Repo:** https://github.com/VDEugenio/AI-Chatbot · **Live:** https://vaughneugenio.com
A production RAG chatbot that answers recruiter questions about Vaughn's experience in natural language — the system you may be talking to right now. React frontend, FastAPI backend, ChromaDB vector store with hybrid retrieval (dense embeddings + BM25 with Reciprocal Rank Fusion), Claude for generation, deployed on AWS App Runner via Docker. Includes an Airflow-based ingestion pipeline that keeps the knowledge base synced with his GitHub activity, an automated eval harness gating CI, and a local Kubernetes (kind) deployment of ChromaDB.
**Status:** Live in production, actively developed.

### 2. VaughnKey — Retrofit Smart Lock
**Repo:** https://github.com/VDEugenio/VaughnKey
A fully removable, battery-powered smart lock built because his landlord wouldn't allow permanent modifications. ESP32 microcontroller, capacitive touch sensing through the door's peephole, BLE proximity authentication, servo-actuated deadbolt, and a deep-sleep architecture drawing ~10µA. Mounts with command strips — zero permanent installation.
**Status:** Working prototype, installed and in daily use on his own door.

### 3. Job Application Tracker
**Repo:** https://github.com/VDEugenio/Job-Application-Tracker
An AI-powered tracker that reads his Gmail (OAuth) and uses Claude Haiku to automatically classify job-application emails — applications, rejections, interviews — replacing a manual spreadsheet. FastAPI backend, SQLite, React frontend, with prompt caching and deduplication by (company, role).
**Status:** Working, in personal daily use.

### 4. Outreach Extension
**Repo:** https://github.com/VDEugenio/outreach-extension
A Chrome extension (Manifest V3) that streamlines LinkedIn job-search outreach. On any LinkedIn profile it enriches the contact via the Apollo.io API (name, current company), generates a personalized connection message from a template — with a character counter for LinkedIn's note limit — and embeds a unique tracking link. The FastAPI + PostgreSQL backend (deployed on Railway) mints short link IDs and records visits; when a recruiter clicks the link, Vaughn's portfolio site resolves it and sends him a real-time Telegram notification. Built to instrument his own job search like a funnel.
**Status:** Deployed and in daily use during his job search.

### 5. ADF Marketplace
**Repo:** https://github.com/VDEugenio/adf-marketplace · **Live:** https://adf-marketplace.vercel.app
A marketplace for uploading, browsing, and downloading Agent Definition Format (.adf) files — "Hugging Face, but for Rawl AI agents." FastAPI backend with PostgreSQL, React frontend, GitHub OAuth, and pluggable storage (local disk or AWS S3). Frontend deployed on Vercel, backend on Render.
**Status:** Deployed and publicly accessible.
