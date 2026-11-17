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

Vaughn has built **eight personal projects**: **1) the AI Resume Chatbot** (production RAG system, github.com/VDEugenio/AI-Chatbot), **2) VaughnKey** (ESP32 retrofit smart lock, github.com/VDEugenio/VaughnKey), **3) the Job Application Tracker** (Gmail + Claude email classification, github.com/VDEugenio/Job-Application-Tracker), **4) the Outreach Extension** (LinkedIn outreach Chrome extension with tracking links — version 1 of ICP Lab, github.com/VDEugenio/outreach-extension), **5) the ADF Marketplace** ("Hugging Face for Rawl agents", github.com/VDEugenio/adf-marketplace), **6) ICP Lab** (AI prospecting and outreach analytics, github.com/VDEugenio/icp-lab), **7) Vinero** (custom personal finance app with a one-tap credit card recommender, private repo), and **8) a Fantasy Football Dashboard** (AI fantasy advisor built for him and his dad, private repo). This is the complete list; details for each below.

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
**Status:** Deployed; used heavily during his career switch into sales. It became version 1 of ICP Lab (project 6), which builds analytics and AI prospecting on top of the same data.

### 5. ADF Marketplace
**Repo:** https://github.com/VDEugenio/adf-marketplace · **Live:** https://adf-marketplace.vercel.app
A marketplace for uploading, browsing, and downloading Agent Definition Format (.adf) files — "Hugging Face, but for Rawl AI agents." FastAPI backend with PostgreSQL, React frontend, GitHub OAuth, and pluggable storage (local disk or AWS S3). Frontend deployed on Vercel, backend on Render.
**Status:** Deployed and publicly accessible.

### 6. ICP Lab — AI Prospecting & Outreach Analytics
**Repo:** https://github.com/VDEugenio/icp-lab
The evolution of the Outreach Extension. Paste a job description and Claude identifies the company, role, and the right people to contact (peers, hiring managers, adjacent leaders, recruiters); Apollo.io finds them; and each person is ranked by predicted engagement based on Vaughn's own outreach history. One click opens the profile and copies a personalized, A/B-tested message with a unique tracking link. Includes funnel analytics, ICP-finder segment analysis, a Gmail reply scanner, and a Work mode he has used for prospecting insurance brokers at Feathery. FastAPI, PostgreSQL, vanilla JS, Claude API, Apollo, deployed on Railway. Full details in icp_lab.md.
**Status:** Deployed and in use.

### 7. Vinero — Personal Finance App
**Repo:** Private
A personal finance app built around Vaughn's own needs and goals. His favorite feature is a one-tap iPhone button that detects what kind of store he's at and recommends which of his credit cards maximizes rewards (about 1.9× the rewards of a flat 2% card, by his estimate), including current Chase Offers and Rakuten deals. Also handles bank sync via Plaid, budgeting, work-reimbursement tracking, and an MCP connection to Claude. Built AI-assisted with Claude Code in about a month. Full details in vinero.md.
**Status:** In personal use (3–5 times a week for the card button).

### 8. Fantasy Football Dashboard
**Repo:** Private
A simple AI fantasy football advisor Vaughn built for himself and his dad (separate accounts for each). It helps him manage his six leagues, lets him consult an AI agent with up-to-date and historical data, and alerts him if he needs to swap a lineup before kickoff.
**Status:** In use during the football season.
