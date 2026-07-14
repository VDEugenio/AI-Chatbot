---
name: Outreach Extension — LinkedIn Job-Search Tooling
description: Chrome extension + FastAPI/PostgreSQL backend that personalizes LinkedIn outreach messages via Apollo.io enrichment and tracks recruiter engagement with unique links and Telegram notifications.
company: personal
repo_url: https://github.com/VDEugenio/outreach-extension
topics: [personal_projects, chrome_extension, job_search, automation, api_integration]
skills: [javascript, chrome_extensions, fastapi, postgresql, api_integration, product_thinking]
story_types: [project, product_pitch, problem_solving]
related_files: [projects_index.md, chatbot_overview.md]
---

# Outreach Extension — Instrumenting the Job Search

**GitHub repository:** https://github.com/VDEugenio/outreach-extension

## What It Is

A Chrome extension that turns cold LinkedIn outreach from a manual chore into an instrumented funnel. Vaughn built it for his own job search: instead of hand-writing connection messages and never knowing if anyone engaged, the extension generates a personalized message in one click and embeds a unique tracking link — so he knows exactly which recruiters clicked through to his portfolio, and when.

## How It Works

1. **Profile detection** — the extension activates on any LinkedIn profile page and extracts the profile identifier from the URL.
2. **Contact enrichment** — it calls the Apollo.io people-match API to resolve the person's first name and current company, with graceful fallbacks (slug-derived name, manual entry) when Apollo has no match or errors.
3. **Message generation** — a templated connection message is populated with the person's name, the target role, and company, editable in the popup with a live character counter for LinkedIn's connection-note limit.
4. **Tracking link** — the extension registers the contact with a FastAPI backend, which mints a short unique ID and returns a tracking URL on Vaughn's own domain (vaughneugenio.com/r/…).
5. **Engagement notification** — when the recipient clicks the link, Vaughn's portfolio backend resolves it, records the visit, and sends him a real-time Telegram notification — closing the loop from outreach to engagement, and landing the recruiter on the portfolio site with the AI resume chatbot.

## Tech Stack

- **Extension:** JavaScript, Chrome Manifest V3, chrome.storage for API-key and state persistence
- **Backend:** FastAPI (Python), PostgreSQL with connection pooling, deployed on Railway
- **Integrations:** Apollo.io enrichment API; the portfolio site's backend (the AI-Chatbot repo) handles link resolution and Telegram notifications

## Why It's Interesting

It's a small system with real product thinking: it identifies the actual bottleneck in cold outreach (no feedback signal), solves it with minimal infrastructure, and integrates with Vaughn's existing portfolio ecosystem — the tracking links deliberately route recruiters to the interactive resume chatbot. It also shows pragmatic engineering judgment: collision-checked short IDs, graceful API-failure fallbacks, and a deploy pipeline (Railway) chosen for speed over ceremony.
