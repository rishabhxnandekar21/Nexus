# CrimeNet AI — Product Requirements Document

| | |
|---|---|
| **Product** | CrimeNet AI (repo codename: `Nexus`) |
| **Version** | 1.0 |
| **Date** | 25 September 2026 |
| **Owners** | Krish Ketankumar Shah, Rishabh Nandekar |
| **Reference brief** | SIH 2026, Problem Statement 26189 — AI-Powered Criminal Network Analysis System |
| **Target date** | Mid-November 2026 (not yet fixed; feature freeze 10 days prior) |
| **Status** | Approved — build starts Week 1 |

---

## 1. Problem

Crime data lives in silos. A police FIR names a suspect. A telecom record shows a
phone number that called another number. A vehicle registry holds an owner name
and a plate. Each database is queried separately, each answer arrives as a row in
a table, and the connection between them — *this phone belongs to the brother of
a man named in an unrelated case, who co-owns the vehicle seen at a third* — only
appears if an investigator happens to notice it manually.

That manual noticing does not scale. Connections across more than two hops are
effectively invisible, and the ones that matter most in organised crime are
exactly the indirect ones.

## 2. What we are building

A system that ingests records from multiple agency sources, resolves records that
refer to the same real-world entity, stores everything as one graph, and gives an
investigator a visual, queryable, time-aware view of that graph — with every
access recorded in a tamper-evident log.

## 3. Goals

| # | Goal |
|---|---|
| G1 | Make multi-hop connections across agency silos visible in one interactive view |
| G2 | Propose identity matches across sources with a stated confidence and an explanation, and require a human to confirm |
| G3 | Enforce agency-level access control so each user sees only the data they are entitled to |
| G4 | Make every access and change provably tamper-evident |
| G5 | Let an investigator ask questions in plain English instead of writing queries |
| G6 | Show how a network evolved over time, and how it would change if a node were removed |

## 4. Non-goals

| # | Explicitly not doing |
|---|---|
| N1 | Predicting crimes or individuals' future criminality. We do network-impact simulation and link prediction over existing data. This distinction is deliberate and will be stated in the viva. |
| N2 | Handling real personal data. All data is synthetic or from public academic datasets. |
| N3 | Live OSINT or web scraping of real people. |
| N4 | Production deployment, horizontal scale, or high availability. |
| N5 | Mobile apps, offline mode, multi-language UI. |
| N6 | Real blockchain. A SHA-256 hash chain provides the tamper-evidence. |

## 5. Users

| Role | Who | Sees |
|---|---|---|
| **Investigator** | Officer attached to one agency | Their own agency's entities and relationships, plus anything flagged `is_shared` |
| **Admin** | Supervisor / nodal officer | Everything across all agencies, plus the audit log and the resolution queue |

Three agencies exist in the demo: `GJ_POLICE` (FIR and case records), `TELECOM`
(call detail records), `RTO` (vehicle registration). Six seeded users, three per
role.

## 6. Success criteria

The project is successful when all five statements below are demonstrably true on
a laptop, offline except for the LLM call, in under five minutes.

| # | Criterion | How it is proved |
|---|---|---|
| S1 | Multi-source data appears as one graph | Dashboard shows nodes sourced from all three agencies with distinct types and relationship labels |
| S2 | The same query returns different data per user | Log out as investigator, log in as admin, same centre node, visibly larger graph |
| S3 | Identity matches are proposed and human-confirmed | Resolution queue shows the seeded duplicate at a plausible score with its matching features listed; confirming merges the nodes on screen |
| S4 | The audit log detects tampering | Edit one `audit_log` row directly in psql, call `/api/audit/verify`, get `valid: false` with the exact `seq` |
| S5 | Time and what-if analysis work | Slider replays six years of network growth; removing the seeded bridge node splits the graph and promotes a new top-betweenness node |

Each of these maps to a phase exit criterion in Section 10.

---

## 7. Feature requirements

Priorities: **P0** must exist or the demo fails. **P1** strongly expected. **P2**
only if time remains after the freeze-date checklist is clean.

### F1 — Authentication and role-scoped access · P0 · *Both (foundation)*

JWT login with username and password. Access token, 12-hour expiry, no refresh
token. Every protected route resolves the current user and their agency.

**Acceptance criteria**
- `POST /api/auth/login` returns a signed token and the user object
- A request with no token or an expired token returns 401
- `GET /api/auth/me` returns username, role and agency
- An investigator calling a graph endpoint receives only rows where
  `agency_id = their agency` or `is_shared = true`
- An admin receives all rows
- A route marked admin-only returns 403 for an investigator

### F2 — Tamper-evident audit log · P0 · *Both (foundation) + Rishabh (UI, verify)*

Append-only log with a SHA-256 chain. Written by a FastAPI dependency so no route
can forget to log.

**Acceptance criteria**
- Every authenticated request that reads or writes graph data appends one row
- Each row stores `seq`, `user_id`, `action`, `resource_type`, `resource_id`,
  `details`, `timestamp`, `prev_hash`, `hash`
- Row 1 uses `prev_hash` of 64 zeros
- `GET /api/audit/verify` recomputes the whole chain and returns
  `{valid, broken_at_seq, checked}`
- Manually altering any field of any row makes verify return
  `valid: false` with that row's `seq`
- A `pytest` test covers chain construction and single-row tampering

### F3 — Unified graph view · P0 · *Krish*

The core screen. A Cytoscape canvas rendering an agency-scoped, date-filtered
subgraph around a chosen centre node.

**Acceptance criteria**
- `GET /api/graph?center={id}&depth=2&from=&to=&types=` returns Cytoscape-format
  `{nodes, edges}`, already scoped and filtered
- Node colour encodes entity type; edge label encodes relationship type
- Node size encodes degree
- Clicking a node opens a side panel with its attributes and its relationships
- Double-clicking a node re-centres the graph on it
- Depth selector supports 1, 2 and 3 hops
- A 2-hop query on the seeded dataset returns in under 1.5 seconds
- 500 rendered nodes pan and zoom without visible stutter

### F4 — Entity search and detail · P1 · *Krish*

**Acceptance criteria**
- `GET /api/entities?type=&q=&limit=` does case-insensitive partial name match
- Results are agency-scoped
- Selecting a result centres the graph on that entity
- Entity detail shows attributes, all relationships with dates, and source agency

### F5 — Network analytics · P1 · *Krish*

**Acceptance criteria**
- `GET /api/graph/analytics` returns degree, betweenness and PageRank per node,
  plus community assignments from greedy modularity
- The UI can colour nodes by community and size them by a chosen centrality
- `GET /api/graph/path?from=&to=` returns the shortest path and the UI highlights
  it
- A "top connectors" list shows the five highest-betweenness nodes in view

### F6 — Temporal view · P1 · *Krish*

**Acceptance criteria**
- Every relationship has `valid_from`; optional `valid_to`
- A dual-handle date slider spanning 2019–2025 filters the rendered graph
- Dragging is debounced at ~150 ms and element filtering runs in `useMemo` keyed
  on the range
- A play button animates the range forward in yearly steps
- The seeded crime ring visibly grows from 3 nodes to its full size across the
  range

### F7 — Synthetic data and demo scenarios · P0 · *Rishabh*

**Acceptance criteria**
- `seed.py` runs from empty and produces, with a fixed random seed, byte-identical
  data on both machines
- Volumes: 3 agencies, 6 users, ~300 persons, ~80 crime events, ~120 phones,
  ~90 vehicles, ~40 locations, ~900 relationships dated 2019–2025
- Names, places and case numbers are Indian-context and plausible
- Data is distributed across the three agencies so scoping is visible
- **Scenario A — crime ring:** ~12 people around one clear central figure, built
  from records in all three agencies, growing over time
- **Scenario B — duplicate identity:** one person present in two agencies under
  slightly different spellings, sharing a phone and an address, designed to score
  ~0.85
- **Scenario C — bridge node:** one person whose removal splits the largest
  component into two roughly equal halves
- `python seed.py --reset` drops, recreates and reseeds in under 30 seconds
- A `--verify` flag asserts all three scenarios are present and prints their IDs

### F8 — Entity resolution · P0 · *Rishabh*

**Acceptance criteria**
- `POST /api/resolution/run` scores candidate pairs of the same entity type
- Scoring signals, each with a documented fixed weight: name similarity
  (token-based), shared phone, shared address or location, shared co-accused,
  date-of-birth proximity
- Scores are explainable — `features` JSONB stores which signals fired and their
  contribution
- Only pairs scoring above a threshold enter the queue as `pending`
- The queue UI shows both records side by side with the contributing features and
  a human-readable reason
- Confirm merges B into A, rewires B's relationships to A, and writes an audit
  entry naming both IDs
- Reject marks the pair rejected and never re-proposes it
- **Nothing ever auto-merges**
- The seeded Scenario B pair appears in the queue, and confirming it visibly
  reduces two nodes to one in the graph

### F9 — What-if and link prediction · P1 · *Rishabh*

**Acceptance criteria**
- `POST /api/graph/whatif` accepts entity IDs to remove and returns before/after
  component count, largest-component size, and the five nodes whose betweenness
  rose most
- The UI shows this as a before/after comparison, not raw JSON
- `GET /api/graph/predict?entity_id=&k=5` returns likely-but-absent links using
  Adamic-Adar and Jaccard, each with its score and the shared neighbours that
  produced it
- Predicted links render as dashed edges, clearly distinct from real ones
- The UI labels this "network impact simulation", never "crime prediction"
- Removing the Scenario C bridge node produces a visible split

### F10 — Natural-language query and case brief · P1 · *Rishabh*

**Acceptance criteria**
- `POST /api/query/nl` sends the question plus a schema description to the LLM,
  which returns **structured filters only**
- Our code executes those filters against Postgres. The LLM never emits SQL and
  never touches the database
- The response returns the interpretation, the filters used, a written answer and
  matching entity IDs, and the UI can centre the graph on those IDs
- `POST /api/query/brief` returns a written summary of an entity's network:
  who they connect to, through what, over what period, and which connections are
  structurally most significant
- Four scripted demo queries have cached responses in a committed JSON file, and
  the client falls back to the cache on any API failure
- Failures degrade to a clear message, never a blank screen

### F11 — Landing and stats page · P2 · *Either*

Counts by entity type, relationships by agency, a timeline histogram, audit-chain
status. Cheap to build, makes the demo feel finished.

---

## 8. Data requirements

Six tables, as specified in `CLAUDE.md` Section 5: `agencies`, `users`,
`entities`, `relationships`, `resolution_candidates`, `audit_log`.

Design rules that must not drift:

- One `entities` table for all node types. Type-specific fields live in
  `attributes` JSONB. No table per entity type.
- Every relationship carries `valid_from`. Without it the timeline cannot work.
- Every entity and relationship carries `agency_id`. Without it scoping cannot
  work.
- `seed.py` is the single source of truth for demo data and is deterministic.
- After foundation week, `models.py` changes only through the schema-change
  protocol in `TEAM-WORKFLOW.md`.

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | 2-hop graph query under 1.5 s; analytics under 3 s; NL query under 5 s including the LLM round trip |
| Scale | ~1,500 entities, ~3,000 relationships. No requirement beyond this. |
| Security posture | Passwords bcrypt-hashed. JWT signed with a secret from `.env`. Tokens in `localStorage` — an accepted MVP trade-off, to be named honestly in the viva alongside the httpOnly-cookie alternative. |
| Reliability | The demo must survive no internet. Everything except the LLM works offline, and the LLM falls back to cache. |
| Legal and ethical | No real personal data at any point. DPDP Act is the governing context and we stay outside its scope by using synthetic data. Stated on the landing page and in the README. |
| Browser support | Latest Chrome on the demo laptop. Nothing else. |

---

## 10. Stages

Seven weeks. Dates assume a mid-November target — shift them together if the date
moves. A stage is not done until its exit criteria pass on **both** machines.

### Week 1 — Foundation · *Both, working together*

The only week you build the same files at the same time. Everything here is the
shared surface that would otherwise cause conflicts for six weeks.

Repo created, `.gitignore` before the first commit, `CLAUDE.md` committed, both
machines running Postgres in Docker. Backend scaffold, `config.py`,
`database.py`, `models.py` complete with all six tables, `auth.py`, `audit.py`,
`schemas.py` with **every** request and response model, and all routers stubbed
returning realistic fake data. Frontend scaffold with Vite, Tailwind, router,
`api/client.js` with the JWT interceptor, `AuthContext`, login page, and an app
shell that navigates between empty pages.

**Exit criteria**
- Both machines run `uvicorn` and `npm run dev` successfully
- Login works end to end with a hardcoded user, and the role appears in the UI
- `/docs` lists every planned endpoint, each returning stub data
- Audit chain writes and verifies, with its pytest passing
- Ownership map in `CLAUDE.md` is committed and agreed

### Week 2 — Data and the first real graph

**Rishabh:** `seed.py` complete, all three scenarios, `--reset` and `--verify`.
**Krish:** `graph.py` — build a NetworkX graph from Postgres with agency scoping
and date filtering; `GET /api/graph` returning real Cytoscape elements.

**Exit criteria**
- `seed.py --verify` passes on both machines with identical output
- `/api/graph` returns real data, and an investigator token and an admin token
  return measurably different node counts

### Week 3 — The graph on screen

**Krish:** `GraphView.jsx`, entity panel, search, depth selector, re-centring.
**Rishabh:** `resolution.py` scoring, `POST /resolution/run`, candidate endpoints,
audit log page with the verify button.

**Exit criteria — this is the project's midpoint and the most important one**
- Two different logins produce two visibly different graphs on screen (S2)
- The audit page shows the chain and reports valid (S4 half-proved)
- Resolution queue returns the Scenario B pair via API

### Week 4 — Resolution and analytics

**Rishabh:** resolution review UI, confirm and reject, merge logic.
**Krish:** analytics endpoint, centrality sizing, community colouring, shortest
path highlight.

**Exit criteria**
- Confirming the seeded duplicate merges two nodes visibly (S3)
- Communities and centrality render correctly on the seeded ring

### Week 5 — Time and what-if

**Krish:** timeline slider, play animation, backend date filtering verified.
**Rishabh:** `analysis.py` — what-if and link prediction endpoints plus their UI.

**Exit criteria**
- The slider replays six years of growth (S5 half)
- Removing the Scenario C bridge node splits the graph on screen (S5 half)

### Week 6 — LLM layer and integration

**Rishabh:** `llm.py`, NL query box, case brief, response cache with fallback.
**Krish:** integration pass — wire every screen together, loading and empty
states, error toasts, consistent styling.

**Exit criteria**
- All four scripted queries work, and still work with the network disconnected
- No screen in the app shows a raw error or an infinite spinner

### Week 7 — Freeze, rehearse, document

**Feature freeze at the start of this week.** No new features. Both: bug fixing,
README with setup steps, architecture diagram, demo rehearsal at least three times
end to end, deck slides 3–6 filled from what actually got built.

**Exit criteria**
- The full demo runs three times without a fix between runs
- A clean clone on a fresh machine reaches a working app using only the README

---

## 11. Work distribution

Split by ownership of demo-visible features, not by lines of code. Each of you
owns features you can demo alone and defend in a viva alone.

| Area | Krish | Rishabh |
|---|---|---|
| **Backend files owned** | `graph.py`, `routers/graph.py`, `routers/entities.py` | `seed.py`, `resolution.py`, `analysis.py`, `llm.py`, `routers/resolution.py`, `routers/query.py`, `routers/audit.py` |
| **Frontend files owned** | `GraphView.jsx`, `EntityPanel.jsx`, `SearchBar.jsx`, `Timeline.jsx`, `Dashboard.jsx`, `EntityDetail.jsx` | `Resolution.jsx`, `AuditLog.jsx`, `NLQueryBox.jsx`, `AnalysisPanel.jsx`, `Stats.jsx` |
| **Features** | F3 unified graph, F4 search/detail, F5 analytics, F6 timeline | F7 seed data, F8 resolution, F9 what-if/prediction, F10 LLM, F2 audit UI |
| **Demo moments** | S1 unified graph, S2 agency scoping, S5a timeline | S3 resolution, S4 audit tampering, S5b what-if |
| **Built jointly in Week 1** | `models.py`, `schemas.py`, `auth.py`, `audit.py`, `config.py`, `database.py`, `main.py`, `api/client.js`, `AuthContext.jsx`, `Login.jsx` | same |

**The interface between you.** `graph.py` exposes one function:

```python
def build_graph(db, user, center_id=None, depth=2, date_from=None,
                date_to=None, types=None) -> nx.Graph
```

Krish owns it. Rishabh's `analysis.py` consumes it and never edits it. This single
contract is what keeps analytics and what-if from colliding with the graph core.

**Shared files neither of you owns alone:** `main.py`, `requirements.txt`,
`package.json`, `models.py`, `schemas.py`. Changes to these follow the protocol in
`TEAM-WORKFLOW.md`.

---

## 12. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Placement interviews take a week from one of you | High | High | Foundation week is joint, so either can cover any area afterwards. Feature freeze gives 10 days of slack. |
| Two Claude sessions refactor each other's files | High | High | Ownership map in `CLAUDE.md`; explicit instruction not to edit or reformat files owned by the other |
| Schema change mid-build breaks the other's database | Medium | High | Schema-change protocol; `seed.py --reset` restores a known state in 30 seconds |
| LLM free-tier quota exhausted or Wi-Fi down at demo | Medium | High | Cached responses committed for the four scripted queries, with automatic fallback |
| Graph rendering stutters with too many nodes | Medium | Medium | Default depth 2, cap returned nodes at 500, aggregate beyond that |
| Scope creep from "one more feature" | High | Medium | Feature freeze is a date, not a feeling. P2 items only after the checklist is clean. |
| Seed data too clean, demo looks fake | Medium | Medium | Include deliberate noise: name spelling variants, missing attributes, dead-end nodes |
| Merge conflicts in `PROGRESS.md` | Medium | Low | Per-person log files; only the phase owner edits their row in the status table |

---

## 13. Out of scope for v1

Real-time ingestion, file upload of real case data, multi-language support,
mobile, export to PDF, notification system, graph editing by investigators,
role hierarchy beyond two roles, and any deployment beyond `localhost`.

---

## 14. Open questions

| # | Question | Needed by |
|---|---|---|
| Q1 | Firm submission date | End of Week 2 — sets the freeze date |
| Q2 | Is there a required report format or template from the department? | Week 5 |
| Q3 | Does the demo happen on your laptop or a lab machine? | Week 6 — changes what must be installable |
| Q4 | Gemini or Groq for the LLM? | Week 5 — whichever free tier is healthier then |
