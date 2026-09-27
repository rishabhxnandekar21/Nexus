# KICKOFF — Read This First

> **You are a Claude Code session working on CrimeNet AI.** Two people are
> building this, each with their own Claude Code session, on their own machine,
> pushing to one GitHub repo. You are one of those two sessions.
>
> **Before anything else, ask the user: "Are you Krish or Rishabh?"** File
> ownership and task assignment depend on the answer, and getting it wrong means
> you will edit files you are not allowed to touch.

---

## 1. Read these four files, in this order

| Order | File | What it gives you |
|---|---|---|
| 1 | `CLAUDE.md` | The project itself — what we're building, hard constraints, the tech stack, the data model, the API surface, coding conventions, and the list of technologies we have explicitly rejected |
| 2 | `PRD.md` | Feature requirements with acceptance criteria, the five demo success criteria, the seven-week stage plan, and who owns what |
| 3 | `TEAM-WORKFLOW.md` | How two Claude sessions share one repo without destroying each other's work |
| 4 | `PROGRESS.md` | What is actually done right now, by whom, and what is next |

Read all four before writing a single line of code. They contradict some common
defaults on purpose — for example, we are not using Neo4j, not using Alembic, not
using `passlib`, and not using Create React App. If you are about to suggest
something, check the rejected-technology table in `CLAUDE.md` Section 2 first.

---

## 2. The project in sixty seconds

Crime data sits in separate silos: police FIRs, telecom call records, vehicle
registrations. An investigator cannot see that a phone number in one case belongs
to a person named in another case, who co-owns a vehicle seen at a third. Those
indirect connections are the ones that matter in organised crime, and they are
invisible to manual work.

**CrimeNet AI** pulls records from three mock agency sources into one graph,
proposes which records refer to the same real person (a human always confirms),
and gives investigators a visual, time-aware, agency-scoped view of that network —
with every access written to a tamper-evident hash-chained audit log.

Built by two final-year students in seven weeks. The deliverable is a five-minute
live demo and a viva, not production software. **Anything a judge cannot see on
screen is not worth building.**

The five things the demo must prove:

1. Multi-source data appears as one interactive graph
2. The same query returns a different graph depending on who is logged in
3. Duplicate identities are proposed with a confidence and an explanation, and a
   human confirms the merge
4. Tampering with any audit row is detected, and the exact row is reported
5. A timeline replays how the network grew; removing a key node splits it

**Stack:** FastAPI · PostgreSQL 16 (local, in Docker) · SQLAlchemy 2.x ·
NetworkX · PyJWT · React 18 + Vite · Cytoscape.js · Tailwind v4 · a hosted LLM API.

---

## 3. Your operating rules

**Every session starts like this:**

1. `git checkout main && git pull --rebase`
2. Read `PROGRESS.md`, then both files in `progress/`
3. `git log --oneline -15`
4. **Report back to the user**: current phase, what is already done, what you are
   about to build, and exactly which files you will touch
5. Wait for confirmation
6. `git checkout -b <phase>-<feature>-<yourname>`

**Never edit a file owned by the other member.** The ownership table is in
`CLAUDE.md`. If you need a change in their file, add a REQUEST entry to
`PROGRESS.md` and tell the user to message their teammate. Do not fix it yourself,
however small it looks.

**No drive-by refactors.** Do not rename, restructure or reformat code you did not
write in this session. The other session wrote it deliberately and its author has
to defend it in a viva.

**Never change `models.py` without the schema-change protocol** in
`TEAM-WORKFLOW.md` Section 6. There are no migrations, so a schema change breaks
the other person's database silently.

**Never add a dependency** that is not in `CLAUDE.md` Section 3 without asking.

**One task at a time.** Finish it, verify it, push it, then stop and report. Do
not run ahead into the next task because you have context left.

**Every session ends like this:** run the verification step, append an entry to
`progress/<yourname>.md`, update your row in `PROGRESS.md`, commit as
`phase-N: <what changed>`, push the branch, open the PR if the task is complete.

---

## 4. Current state: nothing exists yet

The repo is empty. You are starting **Week 1 — Foundation**.

Week 1 is the only week both members work on the same files. This is deliberate:
the shared foundation is about 20% of the code and 80% of the conflict surface, so
it gets built once, together, rather than fought over for six weeks.

**To avoid both sessions building the same thing:** the tasks below form a queue.
Before starting one, mark it 🟡 with your name in `PROGRESS.md`, commit that, and
push it. If a task is already claimed, take the next unclaimed one. Each task is
one branch and one PR.

---

## 5. Week 1 task queue

### W1-1 · Repo bootstrap · *suggested: Krish*

Create the repo, and the `.gitignore` **before the first commit** — not after.

```bash
mkdir Nexus && cd Nexus
git init
# .gitignore must include: .env, __pycache__/, *.pyc, venv/, .venv/,
#   node_modules/, dist/, .DS_Store, *.db, *.log
```

Commit `CLAUDE.md`, `PRD.md`, `TEAM-WORKFLOW.md`, `PROGRESS.md`, this file, a
`README.md` stub, and `.env.example`. Create `progress/krish.md` and
`progress/rishabh.md` with just a heading each. Push to GitHub as `Nexus`, public,
with the description and topics from the README. Then the other member clones it.

`.env.example`:

```
DATABASE_URL=postgresql+psycopg://postgres:crimenet@localhost:5432/crimenet
JWT_SECRET=change-me-in-your-own-env
JWT_EXPIRE_HOURS=12
LLM_API_KEY=
LLM_PROVIDER=gemini
```

**Done when:** both members have cloned the repo and can see all five documents.

---

### W1-2 · Backend scaffold + Postgres · *suggested: Krish*

`backend/requirements.txt` exactly as listed in `CLAUDE.md` Section 3 — no
additions. Then `app/config.py` (pydantic-settings reading `.env`),
`app/database.py` (engine, `SessionLocal`, `get_db` dependency), and `app/main.py`
with CORS allowing `http://localhost:5173` and a `GET /api/health` route.

Postgres runs locally in Docker on each machine:

```bash
docker run --name crimenet-db -e POSTGRES_PASSWORD=crimenet \
  -e POSTGRES_DB=crimenet -p 5432:5432 -d postgres:16
```

**Done when:** `uvicorn app.main:app --reload` starts and `/api/health` returns
`{"status": "ok", "db": "connected"}` with a real query against Postgres.

---

### W1-3 · `models.py` — all six tables · *suggested: Krish*

All six tables exactly as specified in `CLAUDE.md` Section 5: `agencies`, `users`,
`entities`, `relationships`, `resolution_candidates`, `audit_log`.

Critical points, because getting these wrong costs a rewrite later:

- **One `entities` table for all node types.** Type-specific fields go in
  `attributes` JSONB. Do not create a table per entity type.
- Every entity and every relationship carries `agency_id`. Without it, agency
  scoping cannot work.
- Every relationship carries `valid_from`. Without it, the timeline cannot work.
- Index `entities.entity_type`, `entities.agency_id`, `relationships.src_entity_id`,
  `relationships.dst_entity_id`, `relationships.valid_from`.
- `audit_log.seq` is unique and strictly increasing.

Use `Base.metadata.create_all()` in a `init_db()` function. No Alembic.

**Done when:** `python -c "from app.database import init_db; init_db()"` creates
all six tables, and `\dt` in psql lists them.

---

### W1-4 · `auth.py` — JWT and roles · *suggested: Rishabh*

Use the **`bcrypt` library directly** — `bcrypt.hashpw` and `bcrypt.checkpw`. Do
not use `passlib`; it breaks against bcrypt 4.x with a version-detection error.
Use **PyJWT**, not `python-jose`.

Provide: `hash_password`, `verify_password`, `create_access_token`,
`decode_token`, a `get_current_user` FastAPI dependency, and a `require_admin`
dependency. Then `routers/auth.py` with `POST /api/auth/login` (form body) and
`GET /api/auth/me`.

Seed two throwaway users inline for now so login is testable before `seed.py`
exists.

**Done when:** login returns a token; `/api/auth/me` with that token returns the
user; a missing or expired token returns 401; `require_admin` returns 403 for an
investigator.

---

### W1-5 · `audit.py` — hash chain + pytest · *suggested: Rishabh*

Append-only log with a SHA-256 chain. The payload format is specified exactly in
`CLAUDE.md` Section 5 — **use it character for character**, because the verify
function has to recompute it identically.

Expose `write_audit(db, user, action, resource_type, resource_id, details)` and
`verify_chain(db) -> {valid, broken_at_seq, checked}`. Wire it as a FastAPI
dependency so a route physically cannot forget to log. First row uses
`prev_hash = "0" * 64`.

Add `tests/test_audit.py` covering: a chain of five rows verifies valid; altering
row 3's `details` makes verify return `valid: false` with `broken_at_seq == 3`.

**This is the one place a silent bug destroys the whole security claim, and you
cannot see it on screen. That is why it is the only thing with a test.**

**Done when:** `pytest tests/test_audit.py` passes and `GET /api/audit/verify`
returns valid against real rows.

---

### W1-6 · `schemas.py` — every contract, up front · *suggested: Krish*

Write the Pydantic request and response model for **every** endpoint in
`CLAUDE.md` Section 6 — all of them, including features nobody starts until Week
5. This is what stops the frontend from ever blocking on the backend.

At minimum: `LoginRequest`, `TokenResponse`, `UserOut`, `EntityOut`,
`EntitySearchResult`, `GraphNode`, `GraphEdge`, `GraphResponse`,
`AnalyticsResponse`, `PathResponse`, `WhatIfRequest`, `WhatIfResponse`,
`PredictionOut`, `ResolutionCandidateOut`, `NLQueryRequest`, `NLQueryResponse`,
`BriefRequest`, `BriefResponse`, `AuditEntryOut`, `VerifyResponse`.

`GraphResponse` must be Cytoscape-shaped: `{nodes: [{data: {...}}], edges: [{data: {...}}]}`.

**Done when:** every schema imports cleanly and `/docs` shows the full shape of
every response.

---

### W1-7 · Router stubs returning realistic fake data · *suggested: Krish*

Every endpoint in `CLAUDE.md` Section 6 exists and returns hardcoded data that
matches its schema — a fake 12-node graph, three fake resolution candidates, a
fake audit page. All routes are protected and audited exactly as the real ones
will be.

**Done when:** `/docs` lists every planned endpoint and each returns valid,
schema-conformant fake data. The frontend can now be built against this.

---

### W1-8 · Frontend shell · *suggested: Rishabh*

```bash
npm create vite@latest frontend -- --template react
```

Then Tailwind v4 via `@tailwindcss/vite` (no config file), `react-router-dom`,
`axios`, `cytoscape`, `react-cytoscapejs`. Add the `/api` proxy to
`localhost:8000` in `vite.config.js`.

Build: `api/client.js` (axios instance, request interceptor attaching
`Authorization: Bearer <token>` from `localStorage`, response interceptor that
clears the token and redirects on 401), `AuthContext.jsx`, `Login.jsx`, a nav
shell, and empty placeholder pages for Dashboard, Resolution, Audit and Stats.

**Done when:** you can log in through the UI, the logged-in user's name, role and
agency appear in the nav, refreshing keeps you logged in, and logout clears the
token.

---

### W1-9 · Foundation review · *both, together*

Sit down together — physically if possible, one screen. Walk through
`models.py`, `schemas.py`, `auth.py`, `audit.py`. Both of you must understand
every table and every contract, because from Week 2 you stop touching these files
and start depending on them.

Then confirm the ownership table in `CLAUDE.md` and mark Week 1 ✅ in
`PROGRESS.md`.

**Done when:** both machines run backend and frontend, login works on both,
`pytest` passes on both, `/docs` is complete on both, and both members can explain
the schema without looking.

---

## 6. What not to do in Week 1

- Do not write `seed.py` yet. That is W2, and it belongs to Rishabh.
- Do not write `graph.py` or any Cytoscape rendering. That is W2/W3, Krish's.
- Do not touch `resolution.py`, `analysis.py` or `llm.py`. Those are Rishabh's,
  from W3 onward.
- Do not add a dependency beyond `CLAUDE.md` Section 3.
- Do not build an ingestion pipeline, an admin CRUD UI, a settings page, or a
  user-management screen. None are in the PRD.
- Do not make anything configurable, pluggable or extensible. Seven weeks, one
  demo.

---

## 7. After Week 1

From Week 2 the work splits and each of you owns features end to end.

**Krish:** `graph.py` and the graph API, entity search and detail, analytics, the
timeline. Frontend: `GraphView`, `EntityPanel`, `SearchBar`, `Timeline`,
`Dashboard`.

**Rishabh:** `seed.py` and the demo scenarios, entity resolution, what-if and link
prediction, the LLM layer, the audit UI. Frontend: `Resolution`, `AuditLog`,
`NLQueryBox`, `AnalysisPanel`, `Stats`.

The one interface between you, owned by Krish and consumed by Rishabh:

```python
build_graph(db, user, center_id=None, depth=2, date_from=None,
            date_to=None, types=None) -> nx.Graph
```

Rishabh's `analysis.py` calls it. Rishabh never edits `graph.py`.

Week-by-week stages with exit criteria are in `PRD.md` Section 10. Do not start a
week until the previous week's exit criteria pass on **both** machines.
