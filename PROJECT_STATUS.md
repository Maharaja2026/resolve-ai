# ResolveAI — Project Status

Last updated: 2026-11-19

## Completed

- Independent `resolveai/` project created (KnowledgePilot untouched)
- Backend FastAPI app with `/api/v1` routes
- LangGraph agent graph with understand → context → policies → decide → tools → interrupt/approve → respond
- Allowlisted tool registry (10 tools)
- Deterministic eligibility/refund/cancellation/address rules
- Approval service with revalidation + audit logs
- SQL migrations for `resolveai_*` tables + policy RPCs
- Unit tests for eligibility, RRF, tools, roles (**8 passed**)
- Backend `/health` verified on port **8001**
- Frontend JS App Router screens (customer + admin) + `npm run build` succeeded
- Staff `GET /api/v1/agent-runs` list + admin recent-runs table (closes UUID-only lookup gap)
- Docs for architecture/workflow/tools/database/security/approvals/API/testing/evaluation
- Seed script for policies/orders/customers

## Remaining for live demo

- Run SQL migrations + `scripts/seed_demo_data.py` on shared Supabase
- Link auth user → `resolveai_customers.user_id`
- Promote staff roles via SQL only
- Expand evaluation dataset execution and live E2E scenarios

## Ports

- Backend: 8001
- Frontend: 3001

## Start commands

```bash
# backend
cd resolveai/backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001

# frontend
cd resolveai/frontend
npm run dev
```
