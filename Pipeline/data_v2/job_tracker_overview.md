---
name: Job Application Tracker — Overview and Motivation
description: A full-stack personal web app built in a few hours that connects to Gmail via OAuth, uses Claude Haiku to classify job-related emails automatically, and displays everything in a sortable React dashboard — replacing a manual spreadsheet entirely.
company: personal
topics: [personal_project, automation, ai_ml, gmail_api, productivity, rapid_development]
skills: [FastAPI, React, TypeScript, SQLite, Gmail_API, OAuth2, Anthropic, python, full_stack]
story_types: [problem_solving, product_pitch, rapid_prototyping, engineering_rationale]
related_files: [job_tracker_technical.md]
---

# Job Application Tracker

## What It Is

The Job Application Tracker is a full-stack personal web app that automates job application tracking during an active job search. Instead of maintaining a manual spreadsheet, it connects directly to Vaughn's Gmail account via OAuth 2.0, scrapes job-related emails, and uses Claude AI to classify each one — automatically extracting the company name, role, application status, and date. Everything is displayed in a clean, sortable, filterable React dashboard.

It was built in a few hours as a focused solution to a real, immediate problem.

## The Problem

During an active job search, Vaughn was applying to many positions across different companies simultaneously. Application statuses were scattered across an inbox — recruiter responses, interview invites, rejection notices, offer letters — and keeping a manual spreadsheet up to date was tedious and error-prone. Information got lost. Statuses went stale.

The obvious tool for this (a spreadsheet) requires constant manual effort to maintain. Vaughn's approach: automate the tedious part entirely.

## What It Does

- **Gmail integration** — connects via OAuth 2.0 (read-only scope) using the Gmail API; fetches all emails from February 25, 2026 onward
- **AI classification** — each unprocessed email's subject and body is sent to Claude Haiku, which extracts: company name, job role, application status, and application date
- **Smart deduplication** — multiple emails about the same application (e.g., confirmation email + interview invite from the same company/role) are merged into one row; status only advances forward (Applied → Interviewing → Offer/Rejected) and never regresses
- **Local SQLite storage** — results persist in a lightweight local database with one row per unique (company, role) pair
- **React dashboard** — sortable and filterable table with color-coded status badges; manual add/edit for applications the scraper missed
- **On-demand sync** — a Refresh button fetches only new, unprocessed emails; no background polling

## Why It's an Interesting Engineering Project

Despite being built quickly, the project makes several non-trivial engineering decisions:

1. **Using the right AI model for the task** — Claude Haiku instead of Sonnet for cost and speed; this is an explicit model selection decision based on the complexity of the task, not just a default choice.

2. **Prompt caching** — the system prompt is cached with Anthropic's `cache_control: ephemeral`, which significantly reduces token costs when classifying a large inbox during the first sync.

3. **CSRF-safe OAuth** — rather than a single global OAuth flow variable (a common shortcut that introduces a race condition and CSRF vulnerability), pending flows are stored in a state-keyed dictionary, making concurrent auth flows safe.

4. **Status rank enforcement** — the application status follows a strict forward-only progression. A new email can advance a status (Applied → Interviewing) but can never move it backward (Interviewing → Applied). This is enforced at the database upsert level.

5. **Practical scope decisions** — SQLite over Postgres (single-user local app doesn't need a server), Gmail API over IMAP (more reliable and officially supported), on-demand sync over polling (simpler and avoids unnecessary API costs). Each decision is deliberate, not accidental.

## Current Status

Running locally on Vaughn's machine, actively used during his job search. Not deployed — it's a personal productivity tool, not a product.
