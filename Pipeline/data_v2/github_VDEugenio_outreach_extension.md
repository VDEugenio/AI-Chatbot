---
name: outreach-extension (GitHub Repository)
company: personal
source: github_dag
repo_url: https://github.com/VDEugenio/outreach-extension
topics: [github, portfolio, open_source, personal_projects]
skills: []
story_types: [project]
---

This is one of Vaughn's personal projects. **GitHub repository:** https://github.com/VDEugenio/outreach-extension

## Overview

# Outreach Extension

A Chrome extension that turns cold LinkedIn outreach into an instrumented funnel.
Open a LinkedIn profile, click the extension, and get a personalized connection
message with a unique tracking link — so you know exactly who clicked through,
and when.

## Why

Cold outreach is slow and has no feedback signal: personalizing every message
means looking up names, companies, and roles by hand — and after you hit send,
you never know if anyone engaged.

This tool fixes both. It collapses the per-contact workflow (find name, find
company, personalize, generate link) into a single click, making outreach
dramatically faster. And every message carries a short tracking link to my
portfolio site, so every click sends me a real-time Telegram notification —
closing the loop from outreach to engagement.

## How It Works

1. **Profile detection** — the popup reads the active tab and extracts the
   LinkedIn profile slug (`linkedin.com/in/<slug>`).
2. **Contact enrichment** — the profile is matched against the
   [Apollo.io](https://apollo.io) people-match API to resolve first name and
   current company. Falls back to a slug-derived name or manual entry if
   there's no match.
3. **Message generation** — a template is populated with the person's name,
   target role, and company, editable in the popup with a live character
   counter for LinkedIn's connection-note limit.
4. **Tracking link** — the contact is registered with the backend, which mints
   a short unique ID and returns `vaughneugenio.com/r/<id>`.
5. **Engagement tracking** — when the link is clicked, my portfolio backend
   resolves it, records the visit, and pings me on Telegram — landing the
   recruiter on my AI resume chatbot.

## Architecture

```
Chrome extension (Manifest V3)          FastAPI backend (Railway)
  popup.html / popup.js          --->     POST /contacts  -> mint tracking ID
  Apollo.io enrichment                    GET  /r/{uid}   -> resolve + log visit
  chrome.storage (API key

## Recent Activity

- [2026-07-17] Add Gmail send, field persistence, visit IP logging, full-width Regenerate button
- [2026-07-14] docs: add README explaining purpose, workflow, and architecture
- [2026-06-30] Send first_name, last_name, linkedin_url to backend instead of slug
- [2026-06-30] Point extension to Railway backend
- [2026-06-30] Add Procfile and runtime.txt for Railway deployment
- [2026-06-30] Initial commit — Chrome extension + FastAPI backend

## File Structure

- .gitignore
- README.md
- backend/
- manifest.json
- popup.html
- popup.js
