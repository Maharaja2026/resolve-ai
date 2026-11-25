# API Documentation

Base: `http://localhost:8001`  
Prefix: `/api/v1`  
Auth: Bearer Supabase access token

## Key endpoints

- `GET /health`
- `GET /api/v1/me`
- `GET /api/v1/orders`
- `GET /api/v1/orders/{order_reference}/events`
- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{id}/messages` → starts agent run
- `GET /api/v1/agent-runs` (staff) — recent run history
- `GET /api/v1/agent-runs/{run_id}/events`
- `GET /api/v1/approvals` (staff)
- `POST /api/v1/approvals/{id}/approve|reject` (staff)
- `GET /api/v1/tickets`
- `GET /api/v1/analytics/overview` (staff)
