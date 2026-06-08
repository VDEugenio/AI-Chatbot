---
name: Job-Application-Tracker (GitHub Repository)
company: github
topics: [github, portfolio, open_source]
skills: []
story_types: [project]
---

## Overview

# Job Application Tracker

A personal web app that automatically tracks job applications by scraping your Gmail inbox. No manual data entry required — connect your Gmail account, hit sync, and the app uses Claude AI to detect and classify job-related emails into a clean, searchable dashboard.

---

## Features

- **Automatic email scraping** — fetches emails from Gmail (Feb 2026 onward) and classifies them using Claude AI
- **Smart status tracking** — detects Applied, Interviewing, Offer Received, Rejected, and No Response states from email content
- **Deduplication** — merges multiple emails from the same company/role into one entry, advancing status as new emails arrive
- **Manual add & edit** — add applications the scraper missed, or override any field
- **Sortable & filterable table** — sort by any column, filter by status, search by company or role
- **Incremental sync** — subsequent syncs only process new emails, skipping already-processed ones

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | SQLite (local file) |
| Email | Gmail API (OAuth 2.0, read-only scope) |
| AI Classification | Claude Haiku (Anthropic API) |
| Frontend | React 19, TypeScript, Vite |
| Styling | Tailwind CSS v4 |

---

## How It Works

1. You authenticate with Gmail via OAuth 2.0 (read-only access)
2. On sync, the app fetches all emails since Feb 25, 2026
3. Each unprocessed email is sent to Claude Haiku with a classification prompt
4. Claude extracts: company name, role, status, and application date
5. Results are upserted into a local SQLite database — one row per application
6. The React frontend displays everything in a sortable table with color-coded status badges

---

## Setup

See [SETUP.md](SETUP.md) for full step-by-step instructions. In short:

1. Create a Google Cloud project, enable the Gmail API, and download OAuth credentials
2. Get an [Anthropic API key](https://console.anthropic.com)
3. Run the F

## Recent Activity

- [2026-04-18] Add README
- [2026-04-18] Initial commit: Job Application Tracker

## File Structure

- .gitignore
- README.md
- SETUP.md
- backend/
- frontend/
