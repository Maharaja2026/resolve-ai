# Approval Workflow

1. Customer confirms a write action in chat
2. Write tool creates `resolveai_approval_requests` with status `pending`
3. Agent run status becomes `waiting_for_approval`
4. LangGraph `interrupt()` pauses the graph
5. Support/admin reviews in Approvals UI
6. Approve → revalidate → execute simulated action → audit → resume
7. Reject → audit → resume with rejection message → no business mutation
