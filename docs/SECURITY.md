# Security

- JWT validated via Supabase Auth
- Role loaded from `resolveai_user_profiles` (never from client body)
- Public registration always creates `customer` role
- Order tools enforce customer ownership
- Write tools require customer confirmation + staff approval
- Approval execution re-checks eligibility and is idempotent via pending-status compare
- Rejected approvals do not mutate order/payment records
- Secrets are redacted from logs
