---
name: adf-marketplace (GitHub Repository)
company: personal
source: github_dag
repo_url: https://github.com/VDEugenio/adf-marketplace
topics: [github, portfolio, open_source, personal_projects]
skills: []
story_types: [project]
---

This is one of Vaughn's personal projects. **GitHub repository:** https://github.com/VDEugenio/adf-marketplace

## Overview

# ADF Marketplace

A marketplace for uploading, browsing, and downloading `.adf` (Agent Definition Format) files — think "Hugging Face but for Rawl agents."

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ running locally
- (Optional) AWS credentials for S3 storage in production

## Backend Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
# From the repo root
cp .env.example .env
```

Open `.env` and set `DATABASE_URL` to match your local PostgreSQL instance, e.g.:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/adf_marketplace
```

### 4. Create the database

```sql
-- Run in psql or your preferred PostgreSQL client:
CREATE DATABASE adf_marketplace;
```

### 5. Run the development server

```bash
# From backend/
uvicorn main:app --reload
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs

## Running Tests

```bash
# From backend/
pytest tests/ -v
```

The DB connectivity test requires a live PostgreSQL instance matching `DATABASE_URL` in `.env`.

## Storage Backends

Set `STORAGE_BACKEND` in `.env`:

| Value | Behaviour |
|---|---|
| `local` (default) | Files saved to `LOCAL_STORAGE_PATH` on disk |
| `s3` | Files uploaded to `AWS_S3_BUCKET_NAME` |

When using `s3`, also fill in `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`, and `AWS_S3_REGION`. If running on an EC2 instance with an IAM role, you can leave the key fields blank and boto3 will use the instance profile.

## GitHub OAuth Setup

1. Go to https://github.com/settings/applications/new
2. Set **Homepage URL** to `http://localhost:3000` (dev) or your production URL
3. Set **Authorization callback URL** to `http://localhost:8000/auth/github/callback`
4. Copy the **Client ID*

## Recent Activity

- [2026-05-20] Switch auth from cross-site cookies to localStorage Bearer token
- [2026-05-20] Fix cross-site auth: set JWT cookie SameSite=None; Secure for Vercel/Render split
- [2026-05-20] Session 10: Profile page, CORS, Vercel deploy prep
- [2026-05-20] Fix startup crash: use psycopg3 dialect URL so SQLAlchemy doesn't try to import psycopg2
- [2026-05-19] Merge pull request #5 from VDEugenio/claude/keen-hermann-406fb9-session9
- [2026-05-19] Session 9: Upload Form UI — auth guard, file picker, form fields, POST to /agents
- [2026-05-19] Merge pull request #4 from VDEugenio/claude/intelligent-mayer-77485e
- [2026-05-19] Merge master into session branch, keep implemented versions over placeholders
- [2026-05-19] Session 7 & 8: Browse UI + Agent Detail page
- [2026-05-19] Merge pull request #3 from VDEugenio/claude/reverent-edison-7a34cb

## File Structure

- .env.example
- .gitignore
- README.md
- adf-marketplace-brief.md
- backend/
- frontend/
