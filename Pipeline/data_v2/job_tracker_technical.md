---
name: Job Application Tracker — Architecture, Tech Stack, and Key Decisions
description: Full technical breakdown of the job tracker — FastAPI backend with Gmail OAuth, Claude Haiku email classification with prompt caching, SQLite deduplication logic, React frontend, and the security decisions (PKCE, CSRF prevention, read-only scope) made for a local personal tool.
company: personal
topics: [system_architecture, ai_ml, gmail_api, oauth2, sqlite, prompt_caching, security, backend, frontend]
skills: [FastAPI, React, TypeScript, SQLite, Gmail_API, OAuth2_PKCE, Anthropic, prompt_caching, python, pydantic, Tailwind]
story_types: [architecture_design, technical_depth, engineering_decisions, security_thinking]
related_files: [job_tracker_overview.md]
---

# Job Application Tracker — Architecture and Technical Decisions

## System Architecture

The app is split into a Python/FastAPI backend (port 8001) and a React frontend (port 5174) communicating via REST.

```
Browser (React 19 + TypeScript + Tailwind CSS v4)
    ↓ REST API
FastAPI Backend (Python 3.11+)
    ├── Gmail API  ←── reads inbox emails via OAuth 2.0
    ├── Claude Haiku  ←── classifies each email (with prompt caching)
    └── SQLite  ←── stores applications, deduplicates by (company, role)
```

### Sync Flow (what happens when you click Refresh)
1. Backend fetches all Gmail messages from February 25, 2026 onward
2. Skips any message IDs already recorded in the database
3. For each new email, sends subject + body to Claude Haiku
4. Claude returns structured JSON: `{company, role, status, date}`
5. Database upserts the result — merging with existing row if (company, role) already exists, advancing status only if the new status ranks higher
6. Frontend table refreshes with the latest data

## Backend Modules

| Module | Responsibility |
|--------|---------------|
| `main.py` | FastAPI app, CORS config, all route definitions |
| `auth.py` | Gmail OAuth 2.0 flow with PKCE; state-keyed dict of pending flows |
| `gmail.py` | Fetches unprocessed emails from Gmail API; parses headers and body; skips already-processed IDs |
| `parser.py` | Sends email to Claude Haiku; parses structured JSON response |
| `db.py` | SQLite CRUD + upsert logic; deduplicates by (company, role); tracks processed Gmail message IDs per row |
| `models.py` | Pydantic models with input validation (length limits, no future dates) |

## Frontend Components

| Component | Responsibility |
|-----------|---------------|
| `ApplicationTable.tsx` | Sortable, filterable table with clickable column headers |
| `AddEditModal.tsx` | Modal form for manual add and edit of applications |
| `SyncButton.tsx` | Triggers `POST /sync` with loading spinner and result summary |
| `StatusBadge.tsx` | Color-coded pill per status (Applied, Interviewing, Offer, Rejected, No Response) |

## Database Schema

Single table — appropriate for a personal single-user tool:

```sql
applications (
    id                INTEGER PRIMARY KEY,
    company           TEXT,
    role              TEXT,
    status            TEXT,         -- Applied | Interviewing | Offer Received | Rejected | No Response
    applied_date      DATE,
    last_updated      TIMESTAMP,
    source_email_ids  TEXT,         -- JSON array of Gmail message IDs
    notes             TEXT,
    is_manual         BOOLEAN
)
```

Unique constraint on (company, role) enforces deduplication at the DB level.

## AI Integration — Claude Haiku with Prompt Caching

**Model choice: Haiku over Sonnet**

Email classification is a straightforward structured extraction task — the email either mentions a company/role/status or it doesn't. Claude Haiku handles this accurately at a fraction of Sonnet's cost, and the app may classify hundreds of emails during an initial sync. Using a more expensive model would be wasteful.

**Prompt caching**

The system prompt (which defines the classification task, the output JSON schema, and the status vocabulary) is marked with `cache_control: ephemeral` using the Anthropic SDK. Anthropic caches this prompt server-side so that repeated API calls within a short window reuse the cached tokens rather than re-processing them. During a large initial sync, this significantly reduces both latency and cost.

**Classification prompt design**

The prompt instructs Claude to return structured JSON in a fixed schema. If an email is not job-related, Claude returns a null/skip signal. The parser validates the response before inserting into the database.

## Key Technical Decisions

**SQLite over PostgreSQL**
A single-user local app has no concurrent write load. SQLite is zero-config, the file lives on disk next to the app, and there's no server to manage. PostgreSQL would be overkill and add unnecessary operational complexity.

**Gmail API over IMAP**
IMAP is technically viable but fragile — it depends on the email provider's IMAP implementation, handling partial downloads, and managing connection state. The Gmail API is officially supported by Google, returns clean JSON, and has better rate limiting and quota visibility.

**On-demand sync over polling**
Polling would run API calls continuously in the background, accumulating Claude API costs even when the app isn't being actively used. A manual Refresh button keeps the app simple and cost-free when idle.

**Email deduplication by (company, role)**
When Vaughn applied to a job, he'd receive multiple emails over time: an application confirmation, a recruiter response, an interview invite, a rejection or offer. Each of these is a separate email but all belong to the same application. Creating one row per email would produce noise. Merging by (company, role) with status rank enforcement gives a clean, accurate picture of where each application actually stands.

**Status rank enforcement**
The five statuses have a defined rank:
```
Applied (1) → Interviewing (2) → Offer Received (3) / Rejected (3) / No Response (3)
```
On upsert, the new status only replaces the current one if its rank is higher. This prevents a late-arriving confirmation email from rolling back a status that was already advanced to "Interviewing."

## Security Design

Despite being a local personal tool, Vaughn made deliberate security decisions:

**CSRF-safe OAuth flow**
A naive OAuth implementation stores the in-progress flow in a single global variable. This fails under concurrent requests and introduces a CSRF vulnerability — a malicious page can initiate an OAuth flow and steal the resulting token. The fix: store pending flows in a dictionary keyed by the OAuth state parameter, and validate the state on callback. Only the flow whose state matches is completed.

**PKCE**
The OAuth flow uses PKCE (Proof Key for Code Exchange), which prevents authorization code interception attacks even in environments where the client secret is not fully confidential.

**Read-only Gmail scope**
The app requests only `gmail.readonly` — it cannot send, delete, modify, or label emails. Even if credentials were compromised, the blast radius is limited to read access.

**Secrets never committed**
API keys, OAuth credentials, Gmail tokens, and the SQLite database are all gitignored. No secrets in version control.

**Input validation**
Pydantic models enforce length limits on all user-submitted fields and reject future dates on application entries.

**Sanitized errors**
API error responses are sanitized — no internal paths, stack traces, or configuration details are leaked to the client.
