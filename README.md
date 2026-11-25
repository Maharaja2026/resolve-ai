# ResolveAI

Advanced Agentic AI Customer Support & Resolution Platform (portfolio demo).

**DEMO ENVIRONMENT — All order, refund, cancellation, and shipping operations are simulated.**

ResolveAI uses LangGraph to understand support requests, call allowlisted tools, enforce deterministic business rules, request human approval for sensitive actions, and record audit/agent events.

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | Next.js App Router (JavaScript only), Tailwind, Supabase Auth |
| Backend | Python 3.11, FastAPI, LangGraph, LangChain Google/Groq |
| Data | Same Supabase project as KnowledgePilot, `resolveai_*` tables only |
| Embeddings | Local FastEmbed `BAAI/bge-small-en-v1.5` (384-d) |

## Ports

- Frontend: `http://localhost:3001`
- Backend: `http://localhost:8001`

## Quick start

### 1) Database

In Supabase SQL editor, run:

1. `backend/supabase/migrations/001_resolveai_schema.sql`
2. `backend/supabase/migrations/002_resolveai_rls_and_rpc.sql`

### 2) Backend

```bash
cd resolveai/backend
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# reuse KnowledgePilot Supabase + Gemini/Groq keys
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001
```

Seed demo data:

```bash
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

### 3) Frontend

```bash
cd resolveai/frontend
copy .env.example .env.local
npm install
npm run dev
```

### 4) Link a demo customer

1. Register a user in the ResolveAI UI
2. In Supabase, set `resolveai_customers.user_id` for `CUST-1001` (or another seed customer) to that auth user id
3. Optionally set `resolveai_user_profiles.role` to `support_agent` or `admin` for staff demos (SQL only; never via public registration)

## Documentation

See `docs/` for architecture, agent workflow, tools, security, approvals, API, testing, and evaluation.

## Relation to KnowledgePilot

KnowledgePilot remains untouched. ResolveAI shares the Supabase project but uses isolated `resolveai_*` tables/functions.
