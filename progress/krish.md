# Krish — Session Log

> Only Krish writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

### 2026-09-29 · W3 F3b on real data, and the seed digest · `w3-graphview-krish`

**Rishabh - the digest matches.**

```
549e06df2ed10651dbb132bb3eb566d9f8c0d2b45c48215d6b4f9f203c9289e1
```

`python seed.py --reset --verify` on this machine, byte-identical to yours. All
twelve scenario checks PASS here too, largest component 630, bridge removal
splits 316 / 313. That is F7's "byte-identical on both machines" criterion, the
one you could not check alone, and it also settles the Python worry from day
one - you are on 3.13.12, I am on **3.13.9**, and the digest is the same.
**Week 2 is closed on both sides.**

**Done - W3 F3b**
- `GraphView.jsx` (Cytoscape), `EntityPanel.jsx`, `SearchBar.jsx`, rewritten
  `Dashboard.jsx`
- `routers/entities.py` is now real and database-backed
- Entity visibility now has exactly one definition - `entity_scope()` and
  `relationship_scope()` in `graph.py` - used by the graph, search and detail
- `dev_data.py` deleted, as we both agreed. Its twelve records moved inline
  into `routers/graph.py`, the only remaining consumer: the four endpoints
  there that are still stubs.

**The encoding decision, and why it is not a style choice**
Entity type is carried by **shape first, colour second**. I ran the palette
validator rather than picking colours by eye, and six categories cannot be
distinguished by hue: the best available six-hue set scores worst-pair
ΔE **1.6** for deuteranopia against a floor of 8, and **10.6** for normal
vision against a floor of 15. Even evenly-spaced generated hues fail. So six
distinct shapes, an always-on label and a legend carry identity, and colour
only reinforces it. It works in greyscale and for a colourblind viewer, and it
is a good viva answer.

**Verified on the seeded data**

| login | agency | nodes | edges |
|---|---|---|---|
| `investigator` | GJ_POLICE | 402 | 410 |
| `admin` | all | **500 (capped, flagged truncated)** | 768 |
| `telecom_officer` | TELECOM | 217 | 92 |
| `rto_officer` | RTO | 191 | 25 |

Entity counts match your table exactly. **S2 is proved on screen**, not just in
the API - logging in as `telecom_officer` after `investigator` gives a visibly
different network, different size and different shape. That is the W3 exit
criterion.

- Timing: centred queries at depth 1/2/3 return in **296-327ms** against F3's
  1.5s budget.
- Scenario B renders as a demo case: the two `Rakesh` records and the address
  they share, with the shared record ringed.
- Search, centre-on-result, the depth selector (4 / 7 / 9 nodes at depth
  1 / 2 / 3 on a small centre), panel re-centring, and "show whole network" all
  work against real data.
- 36 pytest passing, oxlint clean, production build succeeds, audit chain valid.

**Two defects found and fixed while verifying**
- **402 nodes with every label drawn was an unreadable smear.** Node and edge
  labels are now gated by `min-zoomed-font-size`, so the overview is a legible
  shape and labels appear as you zoom in. This only showed up once there was
  real data - the twelve fake records never exposed it.
- **Picking a search result reopened the dropdown over the graph**, because
  setting the input to the chosen name retriggered the search effect. A ref
  marks that one term change so its response does not reopen the list.

**Double-click to re-centre - now verified**
Confirmed by reaching the live Cytoscape instance and emitting `dbltap` on a
node, rather than trying to land a pixel-perfect double-click on a canvas:
a degree-2 phone took the view from 217 nodes / 92 edges to 3 / 2, centred on
that phone, panel populated. The earlier failures were the test harness, not
the code. **Every F3 acceptance criterion is now met.**

**Files touched**
- `backend/app/graph.py`, `backend/app/routers/entities.py`,
  `backend/app/routers/graph.py`, `backend/dev_data.py` (deleted),
  `backend/tests/conftest.py`, `backend/tests/test_entities.py` (new),
  `frontend/src/components/GraphView.jsx`, `EntityPanel.jsx`, `SearchBar.jsx`
  (all new), `frontend/src/pages/Dashboard.jsx`, `PROGRESS.md`,
  `progress/krish.md`

**Next**
- W4 F5 analytics - centrality, communities, shortest path - which replaces the
  first of the four remaining stubs.

**For Rishabh**
- **Digest matches. Week 2 is closed.**
- **No objection to `.env.example` at 5433** - go ahead.
- Thanks for confirming the relationship-scoping call. The seeded data shows it
  clearly: `telecom_officer` gets 217 nodes but only 92 edges, because most of
  what they can see they cannot see the links of.
- `seed.py` at 487 lines over the 300 guideline - I would leave it. Splitting
  static name pools into a second file to satisfy a line count trades one real
  file for two, and §4 does not list the second one either. Flag it in the viva
  as a deliberate call, the same way I am flagging `schemas.py` at 401.
- Your three router stubs are still unwritten, so `/docs` is still 8 schemas
  short. Not blocking me.

---

### 2026-09-29 · W2 F3a closed out properly · `w2-graph-krish`

Went back over F3a before starting anything else. It was pushed working but not
finished - the exit criterion had only been argued, not shown, and the rewrite
had left debris behind. Six things fixed.

**1. The exit criterion is now actually met, on screen**
`PRD.md` Section 10 asks that "an investigator token and an admin token return
measurably different node counts". Both were returning an empty graph, because
the database is empty. New **temporary** `backend/dev_data.py` loads the twelve
stub records, and the criterion now holds live:

| | nodes | edges |
|---|---|---|
| investigator (GJ_POLICE) | **10** | **9** |
| admin | **12** | **14** |

Hidden from the investigator: `+91 99042 55871` and `GJ-05-KL-9082`, both
another agency and not shared. Still visible because shared: `+91 98250 11223`
and `GJ-01-AB-4417`. And the consequence I flagged is now observable rather
than hypothetical - the shared phone appears with **degree 0**, because the
telecom edge reaching it is scoped out. Both dashboards show these numbers.

`dev_data.py` is not `seed.py` and does not pretend to be: no scenarios, no
volumes, no determinism, no `--reset`. It reads its rows from
`routers/entities.py` so there is one copy of the fake network, and it is
idempotent. It dies with the stubs when F7 lands.

**2. A test that passed only because of ambient state**
`test_empty_database_is_an_empty_graph_not_an_error` asserted an empty database
without making one. It passed while the database happened to be empty and
failed the moment `dev_data.py` ran. It now clears the tables inside the
rolled-back transaction. Proof the rollback holds: the suite deletes every
entity and the twelve rows are still there afterwards.

**3. A duplicated NODE_CAP**
`routers/graph.py` still defined its own `NODE_CAP = 500` from the stub era,
shadowing the real one in `graph.py`. Two copies of a limit are two copies that
drift. Removed.

**4. Four dead imports** left in `routers/graph.py` by the rewrite.

**5. setState called synchronously in an effect** (`AuthContext`). `loading` is
now derived at initialisation from whether a token exists, rather than set true
and immediately corrected. `localStorage` reads are wrapped - they throw in a
private window with site data blocked, and no token is the right answer there,
not a crash on first paint. The frontend now lints clean.

**6. The nav clipped at tablet width** - the agency badge and the logout button
ran off the right edge. The header row and the user block both wrap now.
Checked at 375px: three rows, no horizontal overflow.

**Verified, all of it, after the changes**
- `pytest tests/` - 25 passed
- `npm run lint` - clean, no warnings
- `npm run build` - production build succeeds
- no unused imports anywhere in `app/`, `tests/` or `dev_data.py`
- live: centring at depth 1 and 2, investigator 7 nodes vs admin 10 around the
  same centre, an investigator asking for an RTO-only node gets **404 not 403**
  so existence does not leak, types filter, date windows, 401 without a token
- audit chain valid at 43 rows
- `dev_data.py` run twice: second run creates nothing

**Still not mine to do**
- `seed.py` and the three scenarios are F7, Rishabh's. `dev_data.py` unblocks
  verification; it does not replace F7.
- S2 is **not** marked proved in the demo table. Two different node counts is
  the API half. "Two visibly different graphs" needs the Cytoscape canvas,
  which is W3.

**Files touched**
- `backend/dev_data.py` (new), `backend/tests/test_graph.py`,
  `backend/app/routers/graph.py`, `frontend/src/App.jsx`,
  `frontend/src/context/AuthContext.jsx`, `frontend/src/pages/Dashboard.jsx`,
  `PROGRESS.md`, `progress/krish.md`

**For Rishabh**
- **Run `python dev_users.py && python dev_data.py`** after pulling, or your
  graph will be empty.
- `dev_data.py` is mine and throwaway - delete it when `seed.py` lands rather
  than building on it.
- The scoping consequence is now visible: a shared entity can show with no
  edges. Say if you disagree, it changes the demo.

---

### 2026-09-29 · W2 F3a `graph.py` · `w2-graph-krish`

Started Week 2 with W1-9 still outstanding and eight commits unmerged. That is
against the rule in `PRD.md` Section 10 and I am noting it rather than
pretending otherwise.

**Done**
- `app/graph.py` - `build_graph()`, `can_see_entity()`, `to_cytoscape()`
- `GET /api/graph` now reads Postgres. First endpoint off the stubs.
- `tests/test_graph.py` - 18 tests

**The contract, unchanged from `PRD.md` Section 11**

```python
build_graph(db, user, center_id=None, depth=2, date_from=None,
            date_to=None, types=None) -> nx.Graph
```

Rishabh: call this from `analysis.py`; do not edit `graph.py`. Node attributes
are `name`, `entity_type`, `agency_id`, `agency_code`, `is_shared`,
`source_ref`, `attributes`. Edge attributes are `id`, `rel_ids`, `rel_type`,
`confidence`, `valid_from`, `valid_to`, `source_case`, `agency_id`,
`agency_code`. Graph-level: `truncated`, `center_id`, `depth`.

**Decisions**
- **Entities scope on `agency_id` or `is_shared`; relationships on `agency_id`
  alone.** The `relationships` table has no `is_shared`, and that is right
  rather than an omission - the edge is the sensitive part. That a phone exists
  may be shareable; who called whom is a telecom record a police investigator
  has no claim on. **Consequence worth agreeing before the demo: a shared
  entity can appear with no edges for an investigator.** I believe that is
  correct - they may know the node exists and not its links - but it is a
  judgement call and it will be visible on screen.
- **An invisible centre returns the same 404 as a missing one.** Different
  answers would let an investigator probe for records in other agencies.
- **Date filtering is the overlap test**, carried over from the review fix.
- **Parallel relationships collapse onto one edge**, with every underlying id
  kept in `rel_ids`. The centrality and community algorithms in F5 assume a
  simple graph, and two records of the same link would otherwise double-count.
- **The graph is rebuilt per request**, no cache. At the 1,500-entity scale in
  `PRD.md` Section 9 that is two queries, and it removes every
  cache-invalidation question a persistent graph would add.

**Verified - 25/25 pytest, 18 of them new**
- **S2 is asserted, not eyeballed:** the investigator's graph has strictly
  fewer nodes and fewer edges than the admin's, on rows the test creates. The
  officer sees their own agency plus a shared entity from another, and not an
  unshared one; the telecom edge to that shared phone is absent, so it has
  degree 0.
- Date overlap: an edge from 2019 with no end is still present in a 2024
  window; one that ended in 2020 is not; one that begins in 2021 is absent from
  a 2019 window; an ended edge is visible inside its own window.
- Centring at depth 1 and 2, invisible centre gives an empty graph, types
  filter, `can_see_entity` agreeing with the graph, parallel-edge collapse,
  truncation flagging itself, empty database giving an empty graph.
- Cytoscape ids are strings and every edge endpoint matches a node id.
- Live: `/api/graph` returns `{"nodes":[],"edges":[],...}` for both users,
  404 on a centre that does not exist, 401 without a token. The four stubbed
  graph routes and `routers/entities.py` are unaffected. Audit chain valid
  at 25 rows.

**A frontend bug this surfaced, now fixed**
Switching branches with the Vite dev server running deletes `frontend/` under
it - `main` has no frontend - and the proxy comes back stale, answering
`/api/*` with `index.html`. axios reports a 200, so `Dashboard` read `.nodes`
off an HTML string and **blanked the entire page**. The stale server was my own
doing, but a 200 with the wrong body is not, and a white screen is the worst
possible failure. `Dashboard` now validates the shape before trusting it and
shows a real message. It also has a proper empty state, which is what you see
today. Practical note: **do not switch branches while `npm run dev` is up.**

**Not done**
- No `seed.py` - Rishabh's. Until it runs, `/api/graph` is correctly empty and
  S2 cannot be shown on screen, only in tests.
- `/graph/analytics`, `/path`, `/whatif`, `/predict` and all of
  `routers/entities.py` are still stubs. Analytics is W4, the rest W5, search
  and detail W3.

**Files touched**
- `backend/app/graph.py` (new), `backend/tests/test_graph.py` (new),
  `backend/app/routers/graph.py`, `frontend/src/pages/Dashboard.jsx`,
  `PROGRESS.md`, `progress/krish.md`

**Next**
- W3 F3b - `GraphView.jsx` and the Cytoscape canvas. It needs seed data to be
  worth looking at, so `seed.py` is now the critical path for both of us.

**For Rishabh**
- **`seed.py` is the blocker for everything visual now.** My graph endpoint is
  real and returns nothing because the database is empty.
- `build_graph()` is stable - import it, do not edit `graph.py`. Signature and
  attributes above.
- Please push back on the relationship-scoping decision if you disagree; it
  changes what an investigator sees in the demo.

---

### 2026-09-29 · W1-5 audit.py + hash chain · `w1-5-audit-krish`

**Rishabh - read the first bullet before anything else.**

- **I took W1-5, which your 09-28 log named as your next task.** Nothing had
  been pushed in two days and unpushed work is invisible (TEAM-WORKFLOW 1), it
  was unclaimed in the `PROGRESS.md` table, `app/audit.py` is *Shared - protocol
  required* rather than exclusively yours, and it was blocking my own W1-7
  routes, which were protected but unlogged. Same reasoning you used for taking
  W1-2 and W1-3. Claimed on `main` and pushed before writing a line. **If you
  have a local copy, say so and I will drop mine** - two implementations of the
  one file whose failure is invisible is the worst possible thing to duplicate.

**Done**
- `app/audit.py` - `compute_hash`, `write_audit`, `verify_chain`, `chain_length`
  and an `audited()` route dependency
- `tests/test_audit.py` + `tests/conftest.py` - 7 tests
- `pytest` added to `requirements.txt`, own commit
- My 8 W1-7 routes now take `Depends(audited(...))` instead of
  `Depends(get_current_user)`, closing the gap I flagged in that entry

**Decisions**
- **The payload string is CLAUDE.md Section 5 verbatim** and the module says so
  in a comment. Reordering a field or changing a separator would leave
  `audit.py` self-consistent while silently invalidating every row ever written,
  so `test_payload_format_matches_the_specification` rebuilds the string from
  the spec independently and fails if the two ever diverge.
- **`write_audit` flushes, it does not commit.** The caller owns the
  transaction. That is what lets the whole test suite run inside one rollback
  against the ordinary dev database without leaving rows in an append-only
  table. The `audited()` dependency commits, so a route that later 500s still
  leaves its access logged - the log is of attempts, not successes.
- **A transaction-scoped advisory lock guards the `max(seq)` read.** Two
  concurrent audited requests would otherwise compute the same `seq` and either
  collide on the unique constraint or fork the chain. Not theoretical: the
  dashboard already fires more than one request at a time.
- **Timestamps are naive UTC set in Python**, per the decision in `models.py`.
  A test asserts it, because a tz-aware value would render differently on your
  machine and break the chain in a way nothing on screen would show.

**Verified**
- `pytest tests/` - **7 passed**: five-row chain valid; row 3 `details` edited
  -> `broken_at_seq 3`; row 3 edited *and its hash recomputed* -> still caught,
  at seq 4, because row 4 still carries the old `prev_hash`; a row deleted from
  the middle -> caught; empty chain valid; payload format pinned to the spec;
  timestamps naive UTC.
- **S4 proven end to end against real rows.** Eight routes exercised, chain
  valid over 8 rows. `update audit_log set action='deleted_evidence' where
  seq=5` in psql -> `{'valid': False, 'broken_at_seq': 5, 'checked': 5}`.
  Restored the row -> valid again.
- Correct users logged (investigator 1, admin 2) and the path param captured as
  `resource_id`. **401 and 403 attempts write no row**, because the dependency
  resolves the user before it logs.
- Full 8-route regression unchanged, chain still valid at 13 rows.

**Not done, deliberately**
- **`routers/audit.py` is yours and I did not create it**, so `GET /api/audit`
  and `GET /api/audit/verify` still do not exist. Tamper detection is proven at
  the library level only. Wire `verify_chain(db)` to the endpoint and F2 is
  finished; the function returns exactly the `{valid, broken_at_seq, checked}`
  shape `VerifyResponse` already declares.

**Files touched**
- `backend/app/audit.py` (new), `backend/tests/test_audit.py` (new),
  `backend/tests/conftest.py` (new), `backend/requirements.txt`,
  `backend/app/routers/entities.py`, `backend/app/routers/graph.py`,
  `CLAUDE.md` (team name), `PROGRESS.md`, `progress/krish.md`

**Next**
- W1-9 foundation review, which needs both of us. Nothing else in Week 1 is mine.

**For Rishabh**
- `audited("action", "resource_type")` replaces `Depends(get_current_user)` on a
  route; add `admin=True` for admin-only. Use it on your three routers so the
  logging stays uniform.
- `pytest` is in `requirements.txt` - `pip install -r requirements.txt` again.
- `tests/conftest.py` gives you a `db` fixture that rolls back, if you ever want
  a second test.
- I changed the team name in `CLAUDE.md` Section 1 to `Apostrophe` so it matches
  the README you edited on the 27th.

---

### 2026-09-29 · W1-8 frontend shell · `w1-8-frontend-krish`

Claimed on `main` first, then branched. Stacked on `w1-7-stubs-krish` rather
than `main`, because the shell has nothing real to call without the stub
routers - one PR carries W1-6, W1-7 and W1-8.

**Done**
- Vite + React scaffold, Tailwind v4 through `@tailwindcss/vite`, no config file
- `vite.config.js` with the `/api` proxy to `localhost:8000`
- `api/client.js` - axios on a relative `/api` baseURL, request interceptor
  attaching the bearer token, response interceptor clearing it and redirecting
  on 401
- `context/AuthContext.jsx` - `user`, `loading`, `login`, `logout`
- `pages/Login.jsx`, `pages/Dashboard.jsx`, nav shell with routing in `App.jsx`

**Decisions**
- **React pinned to 18.** The Vite template now scaffolds React 19, but
  `CLAUDE.md` Section 3 says React 18 and `react-cytoscapejs` 2.0.0 does not
  declare React 19 support. That library is my W3 graph canvas and the centre of
  the whole demo; taking a peer-dependency gamble on it to be three months
  newer is a bad trade. Everything installed with zero peer warnings.
- **The login call opts out of the 401 redirect** via a `skipAuthRedirect`
  flag. Without it a wrong password triggers the global handler and blanks the
  form the user is typing into, instead of showing "incorrect password".
- **`AuthContext.loading` starts `true`** and the router waits on it. A refresh
  holds a token but no user yet, so routing before `/auth/me` answers would
  bounce a perfectly logged-in user to the login page.
- **The axios baseURL is relative.** Nothing hardcodes `localhost:8000`; the
  Vite proxy handles dev, and there is no build-time URL to change later.
- **Dashboard actually calls `GET /api/graph`** rather than rendering a static
  box. That is what proves the chain - proxy, interceptor, protected route,
  stub router - is genuinely wired rather than looking wired.

**Ownership**
- `pages/Resolution.jsx`, `AuditLog.jsx` and `Stats.jsx` are Rishabh's, so I did
  **not** create them. Their routes point at one `components/Placeholder.jsx`
  that I own. When he writes a page he adds the file and swaps one line in
  `App.jsx`.

**Verified live in a browser, against the real backend**

| Criterion | Result |
|---|---|
| log in through the UI | investigator and admin both land on the app |
| name, role and agency in the nav | `investigator` / `investigator` / `GJ_POLICE`, and `admin` / `admin` / `GJ_POLICE` |
| refreshing keeps you logged in | hard reload on `/audit` stays on `/audit`, no flash of the login page |
| logout clears the token | `localStorage` empty, redirected to `/login` |
| wrong password | inline "Incorrect username or password", stays on the form |
| deep link while logged out | `/stats` bounces to login, then returns to `/stats` after signing in |
| unknown route | redirects to the dashboard |
| the chain is real | Dashboard shows 12 nodes / 14 edges fetched through the proxy |

**Files touched**
- `frontend/` (new - 16 files), `PROGRESS.md`, `progress/krish.md`

**Next**
- W1-9 foundation review. My side of Week 1 is finished.

**For Rishabh**
- **`package.json` exists and React is 18, deliberately.** Please do not bump it
  to 19 without checking `react-cytoscapejs` first.
- **Your three pages are not created.** Add `pages/Resolution.jsx`,
  `AuditLog.jsx`, `Stats.jsx` when you build them and swap the matching line in
  `App.jsx` - the routes, nav entries and auth guard already work.
- `useAuth()` from `context/AuthContext` gives you `user`, `loading`, `login`,
  `logout`. `client` from `api/client` already attaches the token; just call
  `client.get('/audit')` and do not add your own axios instance.
- Run the frontend with `npm install` then `npm run dev` in `frontend/`. It needs
  the backend on port 8000 and `python dev_users.py` to have been run.

---

### 2026-09-29 · review fixes on W1-7 · `w1-7-stubs-krish`

Self-review of the two stub routers before the PR. Four findings, all four fixed
on the same branch. Only my own files changed - no shared file touched.

**Fixed**
- **Date filter was the wrong predicate.** `_select()` kept edges on
  `valid_from >= date_from`, so a relationship that began before the window and
  never ended disappeared from it. `?from=2023-01-01` returned 2 edges and
  dropped the 2019 `family_of` with a null `valid_to` - a sibling relationship
  that has not ended. Now an overlap test: `valid_from <= date_to` and
  (`valid_to` is null or `valid_to >= date_from`). Same range now returns 10.
  This matters beyond the stub: it is the predicate behind F6 and S5a, and the
  wrong one would have been copied into the real SQL in W2.
- **The centre could be dropped from its own graph.** `keep &= reached | {center}`
  put the centre on the right of an intersection, so a `types` filter excluding
  it removed it while `center_id` still named it. `?center=5&types=person` gave
  nodes 1,2,3 and no 5. Now `keep = (keep & reached) | {center}`.
- **`POST /entities` hardcoded `agency_code="GJ_POLICE"`** while taking
  `agency_id` from the token. Invisible today because `dev_users.py` only makes
  GJ_POLICE users, wrong the moment `seed.py` creates three agencies. Now reads
  the code from the agency row, same pattern as `_user_out` in `routers/auth.py`.
- **`_METRICS` was indexed directly** for every id but hand-written for 1-12, so
  a thirteenth record in `_ENTITIES` would 500 `/graph/analytics`. Now behind a
  `_metric()` helper that falls back to zeros.

**Verified**
- Each fix re-tested live, plus the negative cases: a closed edge
  (`called`, 2021-03-11 to 2021-03-11) is still correctly excluded from a 2023
  window, and `?to=2020-12-31` still keeps only the three edges that had started.
- Full regression over all 8 routes: 12/14 unfiltered, centre preserved at
  depth 1, 404s, 403, 422, path, what-if, predict, 401, 26 schemas in `/docs`.

**Files touched**
- `backend/app/routers/graph.py`, `backend/app/routers/entities.py`,
  `progress/krish.md`

**For Rishabh**
- The date-overlap predicate is the one to reuse when the real query lands.
  Filtering on `valid_from` alone looks right and quietly erases every
  open-ended relationship from any later window.

---

### 2026-09-29 · W1-7 router stubs + environment · `w1-7-stubs-krish`

Stacked on `w1-6-schemas-krish`, so one PR carries both. W1-6 cannot be proved
on its own - an unreferenced Pydantic model never reaches the OpenAPI document,
so "/docs shows every response" needs routes to exist.

**Environment - W1-2 and W1-3 now reproduced on this machine**
- Docker Desktop was dead here: `com.docker.service` was Stopped and starting it
  needs elevation. Started it via a UAC prompt; engine 29.5.3 came up in 10s.
- `crimenet-db` on **5433**, same as Rishabh, same reason - `postgresql-x64-17`
  runs natively on 5432 here. Confirmed we reach the container: `select version()`
  through 5433 reports **PostgreSQL 16.15**, not 17.
- `init_db()` clean. `\dt` gives exactly the six tables, `pg_indexes` the five
  required ones. Independently reproduces his W1-3 result.
- `GET /api/health` -> 200 `{"status":"ok","db":"connected"}`. W1-2 criterion met.
- Login end to end: token, `/auth/me` returns investigator + GJ_POLICE, wrong
  password and unknown username both 401 with an identical message, no token 401.

**Done - W1-7, my two routers only**
- `routers/entities.py` - `GET /entities` with working `type`/`q`/`limit`,
  `GET /entities/{id}` with edges and neighbours, `POST /entities` admin only.
- `routers/graph.py` - `/graph`, `/graph/analytics`, `/graph/path`,
  `/graph/whatif`, `/graph/predict`.
- `main.py` +3 lines to mount them. Nothing else in that file touched.
- Twelve fake records, Indian-context, spread across GJ_POLICE, TELECOM and RTO,
  with 14 dated edges. `graph.py` imports them from `entities.py` rather than
  keeping a second copy, so a search hit and a graph node are the same thing.

**Decisions**
- The stubs **filter for real** rather than returning a constant: centre plus
  depth does a breadth-first walk, `from`/`to` filter on `valid_from`, `types`
  filters by entity type, and `/graph/path` is a real BFS. A frontend built
  against a constant learns nothing about whether its filter wiring works.
- Component counts in `/graph/whatif` are computed for real. Betweenness and
  PageRank are hand-set constants - they are there so the UI has something to
  size and colour by, not as a claim about the fake network. NetworkX replaces
  them in W4/W5.
- `POST /entities` stamps the agency from the caller's token and ignores any
  agency in the body, which is how the real route has to behave.

**Verified - 16/16 live against the running server**

| Check | Result |
|---|---|
| all 8 of my routes in `/docs` | present |
| schemas reaching `/docs` | 5 -> **26** |
| `GET /graph` | 12 nodes, 14 edges, Cytoscape shape, string ids |
| `center=1&depth=1` | narrows to 5 nodes, 5 edges |
| `from=2023-01-01` | 14 edges -> 2 |
| `entities?q=patel` | Ramesh Patel, Suresh Patel |
| `entities?type=vehicle` | both plates |
| `entities/1` | 4 relationships, 4 neighbours |
| `entities/999` | 404 |
| `POST /entities` as investigator | **403** |
| `POST /entities` as admin | 201, agency stamped from token |
| `entity_type: "alien"` | 422, message lists exactly the six `ENTITY_TYPES` |
| `/graph/analytics` | 12 metrics, 2 communities, top connector Ramesh Patel |
| `/graph/path?from=6&to=9` | 4 hops, phone -> Suresh -> Ramesh -> FIR -> Kalupur |
| `/graph/whatif` remove 1 | components 1 -> 2, largest 12 -> 7 |
| `/graph` with no token | 401 |

**Gaps, stated plainly**
- **The stub routes are protected but NOT audited.** KICKOFF W1-7 asks for both.
  `audit.py` is W1-5 and does not exist yet, so there is nothing to call. This
  has to be revisited the moment W1-5 lands, on every route here.
- **No agency scoping.** Investigator and admin get identical graphs today.
  That is S2, the most convincing moment in the demo, and it needs real rows -
  W2, with `build_graph()`.
- `/docs` shows 26 of 34 schemas. The missing 8 are reachable only from
  `routers/resolution.py`, `query.py` and `audit.py`, which are Rishabh's.

**Files touched**
- `backend/app/routers/entities.py` (new), `backend/app/routers/graph.py` (new),
  `backend/app/main.py` (+3 lines), `PROGRESS.md`, `progress/krish.md`

**Next**
- W1-9 foundation review with Rishabh. My side of W1 is done once the PR merges.

**For Rishabh**
- **`require_admin` is now verified over HTTP.** You flagged in your W1-4 entry
  that it was only checked at function level because no admin route existed.
  `POST /api/entities` is that route: 403 for the investigator, 201 for the admin.
- **`main.py` has three more lines** - the import and two `include_router` calls.
- **When `audit.py` lands, my eight routes need the audit dependency.** I have
  not stubbed a fake one, because a fake audit write is worse than none.
- Your three routers are still untouched and still unanswered. Say the word and
  I will stub them, or take them yourself.
- The 12 fake records are throwaway. Delete them in W2 when `seed.py` is real -
  do not build anything on top of them.

---

### 2026-09-29 · W1-6 `schemas.py` · `w1-6-schemas-krish`

**Done**
- 31 new models added to `schemas.py`, 34 in total. The file already existed with
  three auth models; they are untouched and still back login.
- Every model KICKOFF W1-6 names is present, plus `EntityCreate` (`POST /entities`
  needs a request body), `EntityDetailOut`, `RelationshipOut`, `NLQueryFilters`,
  `ResolutionRunResponse`, `ResolutionActionResponse` and `PredictionResponse`.

**Decisions**
- `EntityType`, `UserRole` and `ResolutionStatus` are `StrEnum`s built from
  `ENTITY_TYPES`, `USER_ROLES` and `RESOLUTION_STATUSES` in `models.py`. One
  definition now feeds the CHECK constraints, the request validation and the
  `/docs` dropdown, so they cannot drift.
- Those enums are used on **request** models only. Responses keep plain `str`: a
  row the enum does not know about should be something the UI displays, not a 500
  from response validation on the way out.
- Cytoscape ids are **strings**, not ints. Cytoscape coerces ids to strings
  internally, and an edge whose `source` is `7` while its node id is `"7"` fails
  to render with no error. Getting this wrong is invisible until the graph is
  half empty.
- `GraphResponse` carries `truncated` so the UI can say "showing 500 of N" when
  the cap in `PRD.md` Section 12 kicks in, instead of silently lying.
- `PathResponse.found` is a boolean rather than a 404. No path between two people
  is a real answer to the question, not an error.

**Verified**
- All 34 models import cleanly: `python -c "import app.schemas"` with no errors
- The three auth models survive - asserted by name in the same check, because
  overwriting them was the one failure mode called out in the handoff
- `app.openapi()` builds

**Not verified, and why**
- **`/docs` does not yet show the full shape of every response.** Only 5 schemas
  reach the OpenAPI document, because only the auth routes are mounted and an
  unreferenced Pydantic model does not appear. The rest land when W1-7 wires the
  routers. The W1-6 exit criterion is therefore only half provable on its own.
- **`/api/health` is unverified on this machine.** Docker Desktop will not start
  its engine here - the process runs but the `docker-desktop` WSL distro stays
  stopped and the named pipe never appears, so there is no container and no
  database yet. `init_db()` and `dev_users.py` have not been run. Nothing in W1-6
  touches the database, so this does not block the schemas, but it does block my
  W1-9 sign-off.

**Environment**
- `.venv` on Python **3.13.9** (Rishabh is on 3.13.12 - same minor, worth
  re-checking in W2 when `seed.py` has to be byte-identical)
- All 13 requirements installed. Versions match Rishabh's: SQLAlchemy 2.1.1,
  psycopg 3.3.6, FastAPI 0.141.1, pydantic 2.13.5, bcrypt 5.0.0, NetworkX 3.7,
  pandas 3.0.6. PyJWT is 2.15.1 here against his 2.15.0.
- Local `.env` points at **5433**, same as his, for the same reason: this machine
  runs `postgresql-x64-17` natively on 5432.

**Known deviation**
- `schemas.py` is **401 lines**, over the ~300-line guideline in `CLAUDE.md`
  Section 4. Not split, because Section 4 names exactly one `schemas.py` and W1-6
  asks for every contract in it; splitting it would contradict the documented
  layout and turn one shared file into several. Roughly a third is comments.
  Flagging rather than quietly exceeding it.

**Files touched**
- `backend/app/schemas.py`, `PROGRESS.md` (my row + shared-file log),
  `progress/krish.md` (new entry)

**Next**
- W1-7 router stubs, `routers/graph.py` and `routers/entities.py` only, pending
  the ownership question below.

**For Rishabh**
- **`schemas.py` grew from 3 models to 34.** Your three are untouched. Pull before
  you open it.
- **Read `ResolutionFeature` before you write `resolution.py`.** I guessed a shape
  for the `features` JSONB - `name`, `matched`, `weight`, `contribution`, `detail`
  - so the queue UI has something to render. It is a proposal, not a constraint.
  Change it if the scoring wants a different shape, just tell me.
- `NLQueryFilters` is the structured filter set I assumed the LLM returns in F10.
  Same deal: adjust it when you get to `llm.py`.
- **`pytest`: yes, add it.** Answering your W1-4 question properly. Own commit.
- **Who stubs `routers/audit.py`, `routers/resolution.py`, `routers/query.py`?**
  W1-7 says every endpoint, but those three are yours in the ownership table and
  routers are not in the `PRD.md` Section 11 joint list. I am doing `graph.py` and
  `entities.py` only and will not touch yours until we agree.
- **`.env.example` at 5432 is probably wrong for both of us.** This machine hit
  the identical native-Postgres clash. Your find, your call.
- I moved the three scaffold/models/auth rows in `PROGRESS.md` from "in review" to
  done, since PR #1 merged them. That is a statement about the repo, not a review
  - I have not read that code line by line yet. That belongs in W1-9.
