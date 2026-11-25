# ResolveAI Backend

FastAPI + LangGraph agentic support API.

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001
```

Tests:

```bash
.\.venv\Scripts\pytest.exe -q
```

Seed:

```bash
.\.venv\Scripts\python.exe scripts\seed_demo_data.py
```
