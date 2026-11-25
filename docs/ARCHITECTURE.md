# ResolveAI Architecture

```mermaid
flowchart TD
  UI[Next.js Frontend :3001] -->|Bearer JWT| API[FastAPI :8001]
  API --> Auth[Supabase Auth Validate]
  API --> Graph[LangGraph Agent]
  Graph --> Tools[Allowlisted Tools]
  Tools --> Rules[Deterministic Business Rules]
  Tools --> Policies[Policy RAG Hybrid+RRF]
  Tools --> Approvals[Approval Requests]
  Approvals -->|Human review| Staff[Support/Admin UI]
  Staff -->|Approve/Reject| Resume[Graph Resume]
  Resume --> Exec[Idempotent Simulated Actions]
  API --> DB[(Supabase resolveai_* tables)]
```

## Design principles

- Frontend never executes business logic.
- LLM can propose tool calls; graph + Python validate and execute.
- Sensitive actions require customer confirmation + staff approval.
- Shared Supabase project with KnowledgePilot, isolated `resolveai_*` namespace.
- Gemini primary, Groq fallback for agent decisions.
