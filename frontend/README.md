# ResolveAI Frontend

Next.js 15 (App Router) enterprise helpdesk UI for the ResolveAI demo environment. The app talks to the FastAPI backend at `NEXT_PUBLIC_API_URL` (default `http://localhost:8001`) and authenticates users through Supabase.

## Stack

- Next.js 15, React 19, JavaScript only (`.js` / `.jsx`)
- Tailwind CSS 4, Plus Jakarta Sans
- Supabase Auth (`@supabase/ssr`)
- Sonner toasts, Lucide icons, Recharts (admin analytics), React Markdown

## Setup

```bash
cp .env.example .env.local
# Fill NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
# Ensure NEXT_PUBLIC_API_URL points at the ResolveAI backend (port 8001)
npm install
npm run dev
```

Dev server runs on **http://localhost:3001**.

The UI builds without Supabase credentials: `src/lib/supabase.js` exposes a stub client so `npm run build` succeeds. Auth and API calls require real env values at runtime.

## Routes

| Route | Description |
| --- | --- |
| `/` | Redirect to role home |
| `/login`, `/register`, `/forgot-password` | Auth |
| `/customer` | Customer dashboard (orders, tickets, conversations stats) |
| `/customer/orders` | Order list |
| `/customer/chat` | AI support conversations |
| `/customer/tickets` | Customer tickets |
| `/admin` | Staff dashboard (analytics overview) |
| `/admin/approvals` | Pending approval queue |
| `/admin/tickets` | All tickets |
| `/admin/agent-runs` | Agent run trace lookup |
| `/admin/analytics` | Charts from analytics API |
| `/admin/settings` | Health, LLM status, permissions |

Role-based access uses `GET /api/v1/me` after login (`customer` vs `support_agent` / `admin`).

## Project layout

```
src/
  app/                 # App Router pages
  components/          # chat, dashboard, approvals, orders, agent, shared
  contexts/            # AuthContext
  hooks/               # useApiQuery
  lib/                 # supabase client, utils
  services/            # api.js FastAPI client
  styles/
```

## Scripts

- `npm run dev` — development on port 3001
- `npm run build` — production build
- `npm run start` — start production server
- `npm run lint` — ESLint