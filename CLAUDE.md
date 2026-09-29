# CrimeNet AI — Project Guide

> This file is read automatically at the start of every Claude Code session.
> Read it fully before writing any code. If something here conflicts with a
> suggestion you are about to make, follow this file or ask first.

---

## Session start — do this before writing any code

1. Run `git checkout main && git pull --rebase`
2. Read `PROGRESS.md` — the phase status table and the shared-file log
3. Read both files in `progress/` — the other member's log is how you learn what
   changed since your last session
4. Run `git log --oneline -15`
5. State back to the user: the current phase, what is already done, what you are
   about to build, and exactly which files you will touch
6. Wait for confirmation, then create the branch

## File ownership — do not violate this

| Owner | Files |
|---|---|
| Krish | `app/graph.py`, `app/routers/graph.py`, `app/routers/entities.py`, `src/components/GraphView.jsx`, `EntityPanel.jsx`, `SearchBar.jsx`, `Timeline.jsx`, `src/pages/Dashboard.jsx`, `EntityDetail.jsx` |
| Rishabh | `seed.py`, `app/resolution.py`, `app/analysis.py`, `app/llm.py`, `app/routers/resolution.py`, `app/routers/query.py`, `app/routers/audit.py`, `src/pages/Resolution.jsx`, `AuditLog.jsx`, `src/components/NLQueryBox.jsx`, `AnalysisPanel.jsx`, `src/pages/Stats.jsx` |
| Shared — protocol required | `app/models.py`, `app/schemas.py`, `app/main.py`, `app/auth.py`, `app/audit.py`, `requirements.txt`, `package.json` |

- **Do not edit, refactor, rename or reformat a file owned by the other member.**
  If you need a change there, add a REQUEST entry to `PROGRESS.md` and tell the
  user to message their teammate.
- **Do not reformat or restructure files you did not create in this session**,
  even your own. No drive-by refactors.
- **Never change `app/models.py` without the schema-change protocol** in
  `TEAM-WORKFLOW.md`.
- If a shared file genuinely must change, make the smallest possible change, log
  it in the shared-file section of `PROGRESS.md`, and say so in the PR.

## Session end — always

1. Run the phase's verification step from the PRD and paste the result
2. Append a session entry to `progress/<your-name>.md` using the template there
3. If a phase completed, update only your own row in the `PROGRESS.md` table
4. Commit with `phase-N: <what changed>` and push the branch
5. If the phase is done, open the PR

---

## 1. What we are building

**CrimeNet AI** — an AI-powered criminal network analysis system.

Crime data sits in separate silos (police FIRs, telecom call records, vehicle
registrations). An investigator cannot easily see that the phone number in one
case belongs to a person named in another case, who co-owns a vehicle seen at a
third. Our system pulls these sources into one graph, links entities that refer
to the same real-world thing, and lets an investigator explore the network
visually, ask questions in plain English, and see how the network changes over
time.

Reference brief: Smart India Hackathon 2026, Problem Statement **26189**
(AI-Powered Criminal Network Analysis System), theme *Blockchain &
Cybersecurity*. Team: **Apostrophe**.

### The five things the demo must show

1. **Unified graph** — one interactive network built from three separate mock
   agency sources.
2. **Entity resolution** — the system proposes "these two records are the same
   person, 87% confidence" and a human confirms or rejects it.
3. **Agency-scoped visibility** — the same query returns a different graph
   depending on who is logged in. This is the single most convincing moment in
   the demo.
4. **Tamper-evident audit log** — every action is hash-chained. Edit one row
   directly in the database and the verify endpoint reports exactly where the
   chain broke.
5. **Time travel + what-if** — a slider replays how the network grew; removing
   a node shows who becomes the new key connector.

---

## 2. Hard constraints — read this before proposing anything

- **Two-person student team, roughly two months.** Build the simplest thing
  that demonstrates the capability.
- **This is an MVP for a demo and a viva, not production software.** Clarity
  beats cleverness everywhere.
- **No real personal data. Ever.** All data is synthetic or from public
  academic datasets. No scraping of real people, no live OSINT. India's DPDP
  Act is the legal context; we stay well clear of it by using fake data.
- **Do not add a dependency that is not in section 3 without asking first.**
- **No abstraction until the third repetition.** No repository pattern, no
  service layer interfaces, no dependency-injection framework, no plugin
  architecture. Write the straightforward version.
- **Every feature must be visible on screen.** If a judge or examiner cannot
  see it during a five-minute demo, it is not worth building.

### Explicitly rejected — do not reintroduce these

| Rejected | Reason |
|---|---|
| Neo4j | Postgres + NetworkX covers our scale. One less service to run. |
| Real blockchain (Hyperledger etc.) | A SHA-256 hash chain gives the same tamper-evidence in ~40 lines. |
| spaCy | The LLM does entity extraction better in one prompt. Saves a 500 MB model. |
| Local LLMs (Ollama, Llama) | No GPU, slow on laptops, large downloads. |
| PyTorch / TensorFlow / GNNs | Classical NetworkX algorithms are enough and explain better in a viva. |
| Celery / Redis / RabbitMQ | Nothing we do needs a background queue. |
| Docker for our app | Only used to run Postgres. The app runs directly. |
| Alembic migrations | Use `create_all()` and reseed. Add migrations only when data becomes irreplaceable. |
| Refresh tokens | Access token with 12-hour expiry is enough for a demo. |
| `python-jose` | Barely maintained. Use **PyJWT**. |
| `passlib` | Breaks against bcrypt 4.x with a version-detection error. Use the **`bcrypt`** library directly. |
| Create React App | Deprecated. Use **Vite**. |
| Live web scraping | Ruled out legally and practically. Mock connectors only. |

---

## 3. Tech stack — final

### Backend

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x + `psycopg[binary]` |
| Graph engine | NetworkX (in memory, rebuilt from Postgres) |
| Auth | PyJWT + `bcrypt`, access token only |
| LLM | Gemini or Groq hosted API |
| Audit | `hashlib` SHA-256 chain |

`backend/requirements.txt`:

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg[binary]
pydantic
pydantic-settings
pyjwt
bcrypt
python-multipart
networkx
pandas
google-generativeai
python-dotenv
```

### Frontend

| Layer | Choice |
|---|---|
| Framework | React 18 + Vite |
| Graph UI | `cytoscape` + `react-cytoscapejs` |
| HTTP | `axios` |
| Routing | `react-router-dom` |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`, no config file) |

### Running Postgres

```bash
docker run --name crimenet-db -e POSTGRES_PASSWORD=crimenet \
  -e POSTGRES_DB=crimenet -p 5432:5432 -d postgres:16
```

A free hosted Neon database is an acceptable alternative — it also lets both
teammates share one database.

---

## 4. Repository layout

```
Nexus/
├── CLAUDE.md
├── README.md
├── .env.example
├── backend/
│   ├── requirements.txt
│   ├── seed.py                  # generate synthetic data + load public datasets
│   ├── tests/
│   │   └── test_audit.py        # the one test - hash chain integrity
│   └── app/
│       ├── main.py              # FastAPI app, CORS, router mounts
│       ├── config.py            # pydantic-settings, reads .env
│       ├── database.py          # engine, SessionLocal, get_db dependency
│       ├── models.py            # SQLAlchemy tables
│       ├── schemas.py           # Pydantic request/response models
│       ├── auth.py              # password hashing, JWT, role dependencies
│       ├── audit.py             # hash chain write + verify
│       ├── graph.py             # NetworkX build, scoping, analytics
│       ├── resolution.py        # entity resolution scoring
│       ├── analysis.py          # what-if simulation + link prediction
│       ├── llm.py               # LLM calls + response cache
│       └── routers/
│           ├── auth.py
│           ├── entities.py
│           ├── graph.py
│           ├── resolution.py
│           ├── query.py
│           └── audit.py
└── frontend/
    ├── package.json
    ├── vite.config.js           # includes /api proxy to localhost:8000
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/client.js        # axios instance + JWT interceptor
        ├── context/AuthContext.jsx
        ├── pages/
        │   ├── Login.jsx
        │   ├── Dashboard.jsx        # the main graph screen
        │   ├── EntityDetail.jsx
        │   ├── Resolution.jsx       # review queue
        │   ├── AuditLog.jsx
        │   └── Stats.jsx            # landing / counts page
        └── components/
            ├── GraphView.jsx        # Cytoscape wrapper
            ├── Timeline.jsx         # date range slider
            ├── SearchBar.jsx
            ├── NLQueryBox.jsx
            ├── AnalysisPanel.jsx    # what-if / prediction results
            ├── EntityPanel.jsx
            ├── ErrorBoundary.jsx    # catches a render crash, keeps the app up
            ├── Notice.jsx           # shared loading / empty / error states
            └── Placeholder.jsx      # stands in for a page not written yet
```

Keep files under ~300 lines. If one grows past that, split it by feature.

---

## 5. Data model

Six tables. Everything is scoped to an agency, which is what makes the
visibility demo work.

### `agencies`
`id`, `name`, `code` (e.g. `GJ_POLICE`, `TELECOM`, `RTO`)

### `users`
`id`, `username` (unique), `password_hash`, `role` (`investigator` | `admin`),
`agency_id` → agencies, `created_at`

- `investigator` sees only their own agency's data plus anything marked shared.
- `admin` sees everything.

### `entities`
The unified node table. One row per real-world thing.

`id`, `entity_type`, `name`, `attributes` (JSONB), `agency_id`, `source_ref`
(original record ID in the source system), `is_shared` (bool), `created_at`

`entity_type` is one of: `person`, `vehicle`, `location`, `phone`,
`organization`, `crime_event`.

Type-specific fields live in `attributes` JSONB — age and alias for a person,
plate and model for a vehicle, crime type and status for a crime event. Do not
create a table per type.

### `relationships`
The edges.

`id`, `src_entity_id`, `dst_entity_id`, `rel_type`, `confidence` (float 0–1),
`valid_from` (date), `valid_to` (date, nullable), `source_case` (text),
`agency_id`, `created_at`

`rel_type` examples: `co_accused`, `called`, `owns`, `registered_at`,
`present_at`, `family_of`, `transacted_with`, `suspect_in`, `witness_in`.

`valid_from` / `valid_to` are what make the timeline work. Every relationship
must have a `valid_from`.

### `resolution_candidates`
Proposed "these two entities are the same thing" pairs.

`id`, `entity_a_id`, `entity_b_id`, `score` (float), `features` (JSONB —
which signals matched and their weights), `status` (`pending` | `confirmed` |
`rejected`), `reviewed_by` → users, `reviewed_at`

Confirming a pair merges B into A and rewires B's relationships to A. **Never
auto-merge.** A human always confirms. This is a deliberate design point worth
stating in the viva.

### `audit_log`
Append-only. Never updated, never deleted.

`id`, `seq` (int, strictly increasing), `user_id`, `action`, `resource_type`,
`resource_id`, `details` (JSONB), `timestamp`, `prev_hash`, `hash`

Hash rule:

```python
payload = f"{seq}|{user_id}|{action}|{resource_type}|{resource_id}|{timestamp.isoformat()}|{json.dumps(details, sort_keys=True)}|{prev_hash}"
hash = hashlib.sha256(payload.encode()).hexdigest()
```

The first row uses `prev_hash = "0" * 64`. `GET /api/audit/verify` recomputes
every hash in `seq` order and reports the first mismatch.

---

## 6. API surface

All routes are prefixed `/api`. All except login require a valid JWT.
Every route that reads or writes graph data writes an audit entry.

### Auth
- `POST /auth/login` — form body `username`, `password` → `{access_token, token_type, user}`
- `GET /auth/me` — current user with agency and role

### Entities
- `GET /entities?type=&q=&limit=` — search, agency-scoped
- `GET /entities/{id}` — detail with immediate neighbours
- `POST /entities` — admin only

### Graph
- `GET /graph?center={id}&depth=2&from=&to=&types=` — returns
  `{nodes: [...], edges: [...]}` in Cytoscape element format, already scoped
  to the caller's agency and filtered by date range
- `GET /graph/analytics?center=&depth=` — degree, betweenness, PageRank per
  node, plus detected communities
- `GET /graph/path?from={id}&to={id}` — shortest path between two entities
- `POST /graph/whatif` — body `{remove_entity_ids: [...]}` → before/after
  metrics: component count, largest component size, and the top five nodes
  whose betweenness rose the most
- `GET /graph/predict?entity_id={id}&k=5` — likely-but-missing links using
  NetworkX's Adamic-Adar and Jaccard, with the score and the shared neighbours
  that produced it

### Resolution
- `POST /resolution/run` — score candidate pairs, populate the queue
- `GET /resolution/candidates?status=pending`
- `POST /resolution/{id}/confirm` — merge
- `POST /resolution/{id}/reject`

### Natural language
- `POST /query/nl` — body `{question}` → `{interpretation, filters, answer, entity_ids}`.
  The LLM translates the question into structured filters; **our code runs the
  query against Postgres**. The LLM never writes SQL directly.
- `POST /query/brief` — body `{entity_id}` → a written case summary of that
  entity's network

### Audit
- `GET /audit?limit=100` — recent entries
- `GET /audit/verify` → `{valid: bool, broken_at_seq: int | null, checked: int}`

---

## 7. Build order

Work top to bottom. Each phase should end with something runnable and visible.

### Phase 0 — Scaffold *(~2 days)*
Both folders, `.env.example`, Postgres connecting, FastAPI serving `/api/health`,
Vite dev server rendering a page that successfully calls it. CORS configured for
`http://localhost:5173` on day one.

**Done when:** the React page displays "API healthy" from a live backend call.

### Phase 1 — Data *(~4 days)*
`models.py`, `create_all()`, and `seed.py`.

`seed.py` creates three agencies, six users, and a synthetic Indian-context
dataset: roughly 300 people, 80 crime events, 120 phones, 90 vehicles, 40
locations, and 900 relationships spread across dates from 2019 to 2025. Build in
three deliberate seeded scenarios so the demo always works: a visible crime ring
with a clear central figure, one duplicate-identity pair for the resolution
demo, and one bridge node whose removal splits the network in two.

Optionally also load public academic networks (911 hijackers, Moreno crime,
Noordin Top) as extra demo cases — these are real, citable graphs.

**Done when:** `SELECT count(*)` on every table returns sensible numbers and the
three scenarios are verifiably present.

### Phase 2 — Auth and audit *(~4 days)*
`auth.py`, `audit.py`, login route, `require_role` and `current_user`
dependencies, audit writes wired into a FastAPI dependency so no route can
forget to log. Login page and `AuthContext` on the frontend.

**Done when:** logging in as an investigator versus an admin visibly changes
what the API returns, and `/audit/verify` returns valid.

### Phase 3 — The graph *(~5 days)*
`graph.py` builds a NetworkX graph from Postgres, filtered by the caller's
agency and the requested date range. `GET /graph` returns Cytoscape elements.
`GraphView.jsx` renders them with node colours by entity type and edge labels by
relationship type. Click a node to open the side panel.

**Done when:** two different logins produce two visibly different graphs on
screen. This is the core demo moment — get it right before moving on.

### Phase 4 — Analytics *(~3 days)*
Centrality, community detection, shortest path. Size nodes by centrality, colour
by community, highlight paths.

### Phase 5 — Entity resolution *(~4 days)*
`resolution.py` scores candidate pairs on name similarity, shared phone, shared
address, and shared co-accused. Use simple, explainable weights — not a trained
model — and return the contributing features so the UI can show *why*. Review
queue page with confirm/reject.

**Done when:** the seeded duplicate pair appears in the queue with a sensible
score and confirming it visibly merges two nodes into one in the graph.

### Phase 6 — Timeline *(~3 days)*
Date range slider filtering on `valid_from` / `valid_to`. Debounce ~150 ms;
filter elements in `useMemo` keyed on the slider value.

**Done when:** dragging the slider replays the network growing over six years.

### Phase 7 — What-if and prediction *(~3 days)*
The `/graph/whatif` and `/graph/predict` endpoints plus their UI. Present this
honestly as **network-impact simulation and link prediction**, not crime
forecasting. We can defend what we built; we cannot defend predicting crimes.

### Phase 8 — LLM layer *(~4 days)*
Natural-language query box and case-brief generation.

**Before any demo, cache the responses for the four scripted demo queries into a
JSON file, with a fallback that reads the cache when the API call fails.** Ten
minutes of work that saves the demo from campus Wi-Fi.

### Phase 9 — Polish *(~4 days)*
Loading states, empty states, error toasts, a landing/stats page, README with
setup steps, and a rehearsed demo path.

---

## 8. Conventions

**Python**

- Type hints on function signatures. Pydantic models for every request and
  response body.
- Routes stay thin: validate, call a function in `graph.py` / `resolution.py` /
  `llm.py`, return. No business logic inside route handlers.
- Raise `HTTPException` with a clear `detail` string. No bare `except:`.
- `snake_case` everywhere. Table names plural, model classes singular.

**React**

- Function components and hooks only.
- `axios` instance in `api/client.js` with an interceptor attaching
  `Authorization: Bearer <token>` from `localStorage`, and a 401 handler that
  clears the token and redirects to login.
- Memoize Cytoscape `elements` with `useMemo` and keep the layout config as a
  module-level constant. `react-cytoscapejs` rebuilds the whole graph when the
  `elements` prop identity changes, which makes the layout visibly re-shuffle.
- Keep the token in `localStorage`. It is XSS-vulnerable and that is an
  accepted MVP trade-off — say so in the viva and note that production would use
  httpOnly refresh cookies.

**Config**

- Everything environment-specific goes in `.env`, read through
  `pydantic-settings` in `config.py`. Never hardcode a connection string or an
  API key. Keep `.env.example` current.

**Git**

- Small, working commits. Message format: `phase-N: what changed`.
- Never commit `.env`, `node_modules/`, `__pycache__/`, or generated data.

**Testing**

- No test suite for the MVP. Instead, every phase ends with a manual
  verification step run against real seeded data, as listed in section 7.
- Do add a `pytest` test for the audit chain specifically — it is the one piece
  where a silent bug destroys the whole security claim.

---

## 9. How to work with us

- **Ask before adding a dependency, changing the schema, or restructuring
  folders.** Everything else, just build.
- **Build one phase at a time** and stop for review. Do not run ahead into the
  next phase.
- **Say when something is a bad idea.** If we ask for something that will hurt
  the demo or waste our remaining time, tell us plainly rather than building it.
- **Prefer working over complete.** A feature that runs on seeded data beats a
  more general one that does not run yet.
- **Do not invent facts for the presentation.** No made-up accuracy percentages,
  benchmark numbers, or adoption statistics. If a claim needs a number, tell us
  what to measure.

---

## 10. Vocabulary

| Term | Meaning here |
|---|---|
| Entity | Any node — person, vehicle, phone, location, organization, crime event |
| Relationship | Any edge, always dated with `valid_from` |
| Resolution | Deciding two entity records are the same real-world thing |
| Scoping | Filtering the graph by the logged-in user's agency and role |
| Chain | The SHA-256 hash chain over the audit log |
| What-if | Removing nodes and measuring how the network's structure changes |
| Scenario | A deliberately seeded pattern in the demo data |
