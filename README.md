# Data Analyst Agent

Ask questions about a dataset in plain English, in two modes:

- **💬 Chat** — quick, conversational, multi-turn answers ("What's our best-selling category?" → "And last quarter?").
- **🔬 Research** — a deeper, multi-query analysis with a structured markdown report, key findings, and auto-generated charts.

Ships with a sample dataset (~1,800 customer purchase records: products, categories, payment methods, ratings), loaded as a real `purchases` table in Supabase Postgres — see "Dataset setup" below. Requires a login (JWT auth) to use.

## Architecture

This mirrors the layered design of an existing internal LangGraph project (`Focused Research Agent`), adapted from "web research agent" to "dataset Q&A agent":

```
UI (Streamlit) → API (FastAPI) → Application (use cases) → Graph (LangGraph) → Providers (Groq LLM, Postgres dataset) → Database (Supabase Postgres)
```

Each layer only knows about the layer directly below it — the graph nodes have no idea they're behind HTTP, the API routers have no idea LangGraph exists.

### The pipeline (`src/data_analyst_agent/graph.py`)

Both Chat and Research run the *same* fixed pipeline; a `mode` flag on the shared state makes a handful of nodes branch:

```
init_run → scope_question → generate_queries → execute_queries
                                                     │
                                (results empty/error?) → reflect_and_refine ─┐
                                                     │                       │
                                                     ▼                       │
                                            synthesize_answer  ◄─────────────┘
                                          (research) │  (chat)
                                                      ▼    └──────────┐
                                               build_charts           │
                                                      │                │
                                                      ▼                ▼
                                                  finalize_run ─────► END
```

Any node that hits a real error routes to a terminal `handle_error` node instead — **nodes never raise**, they record the problem on `state["errors"]` and the graph always terminates cleanly. This was a deliberate carry-over from the reference project: it makes the pipeline trivially testable (every node is a pure function you can call with a plain dict) and means a single bad LLM response degrades to "I couldn't complete that" instead of a 500.

- `scope_question` — chat: resolves the question to one standalone sub-question (using conversation history for follow-ups like "and last month?"). Research: splits it into 2–4 facets (overall trend, breakdown by category, outliers, etc).
- `generate_queries` — turns each sub-question into a PostgreSQL `SELECT` query against the dataset's schema.
- `execute_queries` — runs them through the sandboxed `DataSourceProvider`.
- `reflect_and_refine` — if a query errored or returned nothing, asks the LLM to fix it (bounded to 1 retry).
- `synthesize_answer` — chat: a short conversational reply. Research: a structured markdown report (Overview / Key Findings / Analysis / Recommendations).
- `build_charts` — **research only, and deliberately not LLM-driven**: a small heuristic picks a category/date column + a numeric column from each query result and renders a bar or line chart. See "Decisions & trade-offs" below for why.

### Folder layout

```
src/data_analyst_agent/
  api/            FastAPI app, routers, Pydantic schemas, exception handling
  application/    use cases (chat_use_case, research_use_case), validation, state normalization
  auth/           JWT bearer auth: register/login, bcrypt hashing, get_current_user dependency
  caching/        response cache (Research mode only) -- Redis if REDIS_URL is set, else in-memory
  config/         one settings module per concern, env-var driven
  core/           rate limiting (also Redis-backed if REDIS_URL is set), request logging middleware
  database/       SQLAlchemy models (User, AnalysisRun) + repository pattern (only repository.py issues queries)
  interfaces/     LLMProvider / DataSourceProvider abstract contracts
  nodes/          the LangGraph pipeline steps described above
  reliability/    circuit breaker around LLM calls
  services/       concrete providers: Groq LLM, Postgres (Supabase) dataset engine
  tools/          dev utility to export the graph diagram
  ui/             Streamlit app (api_client.py talks HTTP, views.py renders, app.py wires them + login/register)
  graph.py        builds the LangGraph pipeline
  state.py        shared TypedDict state
tests/            unit + integration tests with fake LLM/dataset providers (no network needed)
docs/
  supabase_schema.sql   run once in Supabase's SQL Editor to create the 3 tables
scripts/
  upload_dataset.py      one-off loader: Excel file -> `purchases` table
```

## Dataset setup (Supabase)

The dataset, user accounts, and conversation history all live in a Supabase Postgres project (free tier).

1. Create a Supabase project, then run `docs/supabase_schema.sql` in its SQL Editor (creates `users`, `purchases`, `analysis_runs`).
2. Get the **Session pooler** connection string (Supabase dashboard → Connect → Connection string → Session pooler) — the free tier's "direct connection" is IPv6-only and often fails to resolve; the pooler is IPv4-compatible.
3. Load the sample data: `python scripts/upload_dataset.py "postgresql+psycopg2://...your pooler string..."` (expects an Excel file at `data/Customer-Purchase-History.xlsx` with columns `CustomerID, Product, PurchaseDate, Quantity, UnitPrice, CustomerName, ProductCategory, PaymentMethod, ReviewRating, TotalPrice` — supply your own if you're starting fresh; this repo's copy of the Supabase project already has the data loaded).
4. Put the same connection string (with `+asyncpg` instead of `+psycopg2`) in `.env` as `DATABASE_URL`.
5. Run `docs/dataset_reader_role.sql` (set a password first) and put the same pooler string, with user `dataset_reader.<project-ref>` and that password, in `.env` as `DATASET_DATABASE_URL`. This is the role the LLM's SQL runs as.

## Running it

### Docker (recommended)

```bash
cp .env.example .env
# edit .env: GROQ_API_KEY, DATABASE_URL, AUTH_SECRET_KEY (see Dataset setup above)

docker compose up --build
```

This also starts a local Redis container (used for the response cache + rate limiting, with an in-memory fallback if you run without Docker/Redis).

- API + docs: http://localhost:8000/docs
- UI: http://localhost:8501 — register an account or log in, then use Chat/Research

### Locally, without Docker

```bash
uv venv && uv pip install -e ".[dev]"   # or: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env   # set GROQ_API_KEY, DATABASE_URL, AUTH_SECRET_KEY

# Terminal 1
uvicorn data_analyst_agent.api.app:create_app --factory --reload

# Terminal 2
streamlit run src/data_analyst_agent/ui/app.py
```

`REDIS_URL` left blank means the cache/rate-limiter fall back to in-memory automatically — no Redis needed to run locally.

### Tests (no API key, Supabase, or Redis needed — LLM/dataset are faked)

```bash
pytest -q
```

## Decisions & trade-offs

**Real external services where the risk is low, in-memory/local where it isn't.** Supabase (Postgres) and Groq are both live network dependencies — genuinely useful, but they're also the two things that could fail during a demo if the network hiccups. Redis, by contrast, runs as a local container in the same Docker network as the app, so it carries none of that live-demo risk; it's purely a "does this survive a restart" upgrade, with an in-memory fallback if `REDIS_URL` isn't set. The abstractions that make each of these swappable (repository pattern, provider interfaces, a `ResponseCache` protocol) stay in place regardless of which backend is actually wired up.

**Fixed pipeline over LLM tool-calling.** The agent doesn't decide *whether* to query the dataset — it always does, deterministically, the same way the reference project always searches the web. For one well-known dataset this is more predictable and testable than open-ended tool-calling would be, at the cost of flexibility if the assistant needed to do arbitrarily different *kinds* of things later (call an external API, write a file, etc).

**Charts are rendered by a heuristic, not by LLM-generated code.** The tempting alternative — ask the LLM to write matplotlib/pandas code and `exec()` it — is a second, much riskier "generate and run arbitrary code" surface stacked on top of the SQL one. Instead, `build_charts` looks at the shape of an already-validated query result (one categorical/date column + one numeric column) and picks a bar or line chart. Less flexible (no scatter plots, no multi-series), but the *only* LLM output that ever gets executed anywhere in this app is sandboxed, read-only SQL.

**SQL is validated, not trusted.** The LLM's queries are treated as untrusted input: `DataSourceProvider.execute_query` rejects anything that isn't a single `SELECT`/`WITH` statement, blocks DDL/DML keywords, and caps returned rows. This matters more here than in the reference project, where "tool use" was a fixed web-search call with no user-influenced code path. The regex is only the first layer, though: it stops writes but not *which table* a `SELECT` reads, and `users` (password hashes) lives in the same database. So the dataset connection uses a separate least-privilege Postgres role (`docs/dataset_reader_role.sql`) that can only `SELECT` from `purchases`, with read-only transactions and a 10s statement timeout. A prompt-injected `SELECT * FROM users` is then refused by Postgres itself (`permission denied`), whatever the prompt or the regex let through.

**Chat is cached never, Research is cached by exact question text.** Chat is inherently conversational — the same words can mean something different depending on history, so caching it would be actively wrong. Research is stateless and expensive (multiple LLM calls); caching it means asking the same deep question twice in a demo is instant the second time.

**Real JWT auth, not a single shared API key.** Every chat/research/dataset/conversations call requires a logged-in user (`auth/security.py`: bcrypt password hashing + JWT issuing/verification, ported near-verbatim from the reference project's approach). Conversation history (`analysis_runs.user_id`) is scoped per user.

**Any LLM backend can be swapped in via the `LLMProvider` interface** (`interfaces/llm_inference.py`); only Groq's free tier is wired up (`services/llm_provider_groq.py` + `llm_factory.py`) since it's fast and free, but adding e.g. Ollama for a fully offline setup is a new provider file + one branch in the factory, not a rewrite — same pattern as swapping the dataset backend (`interfaces/data_source.py`).

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | liveness check |
| POST | `/api/v1/auth/register` | none | create an account, returns a JWT |
| POST | `/api/v1/auth/login` | none | returns a JWT |
| GET | `/api/v1/dataset/schema` | bearer | columns, dtypes, sample values, row count |
| POST | `/api/v1/chat` | bearer | `{question, conversation_id?}` → short answer, threads conversation |
| POST | `/api/v1/research` | bearer | `{question}` → markdown report + key findings + charts |
| GET | `/api/v1/conversations` | bearer | list your past chat conversations |
| GET | `/api/v1/conversations/{id}` | bearer | full turn history for one conversation |

Full interactive docs at `/docs` once the API is running.
