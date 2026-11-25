# Database

ResolveAI uses the shared Supabase project with isolated objects:

- Tables: `resolveai_*`
- RPCs: `resolveai_match_policy_chunks`, `resolveai_keyword_policy_chunks`

KnowledgePilot tables are never modified.

## Migrations

1. `001_resolveai_schema.sql`
2. `002_resolveai_rls_and_rpc.sql`

## Core entities

customers → orders → order_events  
conversations → messages → agent_runs → agent_events / tool_executions  
approval_requests → refund_records  
policy_documents → policy_chunks (vector 384 + FTS)
