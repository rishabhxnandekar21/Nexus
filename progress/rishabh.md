# Rishabh — Session Log

> Only Rishabh writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

### 2026-09-30 · W3 F2, W3/W4 F8, W5 F9, W6 F10 · four branches

Merged Krish's whole chain into `main` first (`ac0f495`, 22 commits, zero
conflicts) because every frontend page below builds on his shell, his `Notice`
component and his `useAuth()` hook. Reviewed before merging: the audit payload
matches §5 character for character, `audit.py` honours the naive-UTC requirement
from `models.py`, `schemas.py` kept my three auth models, `models.py` untouched,
and his suite passes here. **His 22 commits went in without a PR** - my fault for
merging locally, and the Decisions log wants PRs on both profiles, so his future
branches should get one opened first.

Then four tasks, one branch each, each verified before the next started.

---

**W3 F2 · audit routes and page · `w3-audit-rishabh` · S4 PROVED**

`routers/audit.py` - `GET /api/audit` and `/audit/verify`, admin only per §5.
Both are themselves audited: reading the log appends to the log, which is right.

`AuditLog.jsx` - verify button, the chain as a table with each row's `prev_hash`
beside its `hash`, the broken row highlighted red. A 403 renders as "admin only",
not an error, because an investigator hitting it has done nothing wrong.

Verified 16/16, including the tamper case the PRD actually specifies:

| | |
|---|---|
| tampered `details` on seq 3 | `{valid: false, broken_at_seq: 3, checked: 3}` |
| deleted a middle row (seq 4) | detected, reported at seq 5 — the row after the gap |
| both restored afterwards | chain verifies valid again |

It leaves a working database rather than a broken one.

The page first went in with a `set-state-in-effect` lint warning — the class Krish
cleared in W6. Rewrote it as a promise chain inside the effect with an `attempt`
counter, matching `AuthContext`, rather than suppressing it.

---

**W3 F8a + W4 F8b · resolution · `w3-resolution-rishabh` · S3 PROVED**

Five signals, fixed documented weights summing to 1.0 — name 0.35, shared phone
0.25, shared address 0.20, shared co-accused 0.10, DOB proximity 0.10 — each
recorded in `features` with what it contributed. Not a trained model.

Name similarity is token-based and symmetric. A whole-string ratio badly
understates `Rakesh Kumarbhai Yadav` against `Rakesh Kumar Yadhav`.

Blocking keeps the cost honest: 303 persons is ~45,000 pairs for a handful of real
matches, so only pairs sharing a name token or a phone or location are scored.
2,634 pairs in 530ms.

**The seeded Scenario B pair scores 0.8556** against the ~0.85 `seed.py` was built
for, and the contributions sum to the score.

The merge deletes record B rather than leaving it edgeless, because `build_graph`
adds every visible entity as a node — an edgeless B would still render, and F8
requires two nodes becoming one. So the candidate rows pointing at B go too, and
the permanent record is the audit entry naming both ids, hash-chained. Stronger
than a mutable queue row.

Confirm asks twice. It is the one irreversible action in the app.

Verified 30/30: confirm rewires 1 relationship, removes B from the graph, drops
the database 650 → 649, 404s the merged record, writes an audit entry naming both
ids, leaves the chain valid, and refuses a second confirm. Reject is never
re-proposed.

**Bug found:** `models.py` declares the foreign keys but no ORM `relationship()`,
so SQLAlchemy did not know `resolution_candidates` depends on `entities` and
ordered the entity DELETE first in one flush. Postgres rejected it. Fixed by
flushing the candidate deletes first.

---

**W5 F9 · analysis · `w5-analysis-rishabh` · S5b BLOCKED on Krish**

`analysis.py` consumes the graph `build_graph()` returns and never edits it.

- `what_if` — before/after node, edge, component and largest-component counts,
  plus the five nodes whose betweenness rose most. Exact betweenness, not
  k-sampled: sampling noise would make a node appear to rise for no reason on a
  screen whose job is to name the new key connector.
- `predict_links` — NetworkX Adamic-Adar and Jaccard over non-adjacent pairs with
  a neighbour in common.

**Removing the Scenario C bridge takes the largest component 500 → 250 + 250 as
admin (497ms), and 317 → 169 + 148 as an investigator (220ms).**

`tests/test_analysis.py`, 11 tests, including one proving Adamic-Adar ranks a
quiet shared contact above a hub. The S5b test needs a read-only session because
the shared `db` fixture empties every table — right for unit tests, wrong for a
claim about `seed.py`'s output.

**S5b is not closed.** `POST /graph/whatif` and `GET /graph/predict` are still the
W1-7 stubs on hardcoded data, in `routers/graph.py`, which is Krish's. REQUEST
with the exact replacement bodies is in `PROGRESS.md`.

---

**W6 F10 · LLM layer · `w6-llm-rishabh` · PROVED OFFLINE**

The model returns filters only; `clean_filters()` drops anything outside a fixed
allow-list before a query exists. A question containing `DROP TABLE entities`
returns an ordinary scoped result.

Everything degrades to `demo_cache.json` and then to a deterministic answer. The
cache supplies phrasing only — counts and ids are always recomputed live, so
nothing on screen is a number from a recording.

**All four scripted queries answer in under 50ms with `LLM_API_KEY` empty**: 200
police records since 2023, 18 named Rakesh, 62 phones with calls overlapping
2020-2022, 40 vehicles tied to an address.

**Two bugs found, both mine:**
1. `entity_scope()` returns **None** for an admin meaning "no restriction" —
   `graph.py` says so plainly and I did not honour it. `.where(None)` matches
   nothing in SQLAlchemy 2.x, so an admin got 0 results and an investigator 13.
   Exactly backwards, and an ugly thing to find mid-demo.
2. A question yielding no filters returned every record in scope, capped at 200.
   That looks like an answer while being none. Now returns nothing and says why.

---

**Totals**

58 pytest passing, frontend lints clean and builds, `seed.py --verify` digest
unchanged at `549e06df…`.

**Files touched**
- new: `app/routers/audit.py`, `app/resolution.py`, `app/routers/resolution.py`,
  `app/analysis.py`, `app/llm.py`, `app/routers/query.py`, `app/demo_cache.json`,
  `tests/test_analysis.py`, `pages/AuditLog.jsx`, `pages/Resolution.jsx`,
  `pages/Analysis.jsx`, `components/AnalysisPanel.jsx`, `components/NLQueryBox.jsx`
- shared: `app/main.py` (six lines of router mounts), `App.jsx` (routes + one nav
  entry), `PROGRESS.md`

**Next**
- F11 Stats is **not started and not on the phase board** — it is P2 in PRD §7 and
  needs a counts endpoint that §6 does not define, so I have not invented one. The
  nav still points `/stats` at a placeholder.
- W1-9 foundation review, still outstanding.

**For Krish**
- **The REQUEST in `PROGRESS.md` is the only thing blocking S5b.** Two route
  bodies, three lines each, exact code given. `analysis.what_if` already returns
  the `WhatIfResponse` shape.
- **`GraphView.jsx`:** predicted links want dashed edges. `GraphEdgeData.predicted`
  already exists for it. Not urgent — my panel lists them with dashed borders.
- **`Dashboard.jsx`:** it keeps `centerId` in local state, so I cannot deep-link a
  query result to a centred graph. If you read `?center=` from the URL, the NL
  query box can hand off to your canvas, which is what F10 asks for.
- **I agree on raising the ~300-line guideline**, and it needs writing down once
  rather than justifying per file. `resolution.py` is 300 and `AnalysisPanel.jsx`
  is 290, so I have added to the problem.
- `.env.example` is still 5432. Both machines clash. I will flip it unless you say
  otherwise.
- **Your PageRank stays hand-written.** Do not add scipy. "We implemented power
  iteration" is a better viva answer than "we imported it".

---

### 2026-09-29 · W2 F7 `seed.py` + three scenarios · `phase-1-seed-rishabh`

Branched off `main`, not off Krish's chain. `seed.py` needs only `models.py`,
`database.py` and `auth.py`, all merged in PR #1, so this PR stays independently
reviewable and does not inherit five unreviewed tasks.

**Volumes — F7's targets, actual in brackets**

3 agencies [3] · 6 users [6] · ~300 persons [303] · ~80 crime events [80] ·
~120 phones [121] · ~90 vehicles [90] · ~40 locations [41] · ~900 relationships
[940] · plus **15 organizations**, not in F7's list, added so all six
`entity_type` values exist in the data.

`--reset` runs in **1.6 seconds** against F7's 30-second budget.

**Determinism — proved, not asserted**

One `random.Random(20260929)` drives every choice, inserts happen in fixed order,
and `--reset` resets the SERIAL sequences, so ids are stable too. `--verify` prints
a **content digest** — SHA-256 over every agency, user, entity and relationship in
id order — so both machines compare one string instead of trusting each other.

Two full wipe-and-reseed cycles gave the identical digest:

```
549e06df2ed10651dbb132bb3eb566d9f8c0d2b45c48215d6b4f9f203c9289e1
```

**Krish: run `python seed.py --reset --verify` and tell me if your digest differs.**
That is the F7 "byte-identical on both machines" criterion, and it is the one thing
I cannot check alone.

Deliberately excluded from the digest: `password_hash` (bcrypt salts differ every
run) and `created_at` (Postgres generates it). Neither is data we authored, and
including either would make the digest useless.

**The topology decision that makes Scenario C work**

Scenario C needs removing one person to split the largest component roughly in
half. That is only true if nothing *else* joins the two sides — and with 940 random
relationships over 650 entities, an accidental second path is close to certain. So
the whole population is **partitioned into two halves**: persons, phones, vehicles,
locations, crime events and organizations are each split, every background
relationship stays inside its half, and the two halves meet only at the bridge.
Each half gets a random spanning tree first so it is guaranteed to be one
component, then extra edges on top.

Scenario B's two records also sit in the *same* half deliberately — they share a
phone and an address, so splitting them across halves would create a second bridge
and quietly break Scenario C.

**Verified — all three scenarios**

| Scenario | Result |
|---|---|
| **A — crime ring** | 12 people around one central figure, 15 person-neighbours once background edges are counted. Spans `person`, `phone`, `vehicle`, `crime_event` — all three agencies. Edges dated 2019, 2020, 2021, 2022, 2023, 2024, 2025, so F6's slider has seven steps to replay. |
| **B — duplicate identity** | `Rakesh Kumarbhai Yadav` (GJ_POLICE) vs `Rakesh Kumar Yadhav` (RTO). Share one phone entity and one location entity. DOBs two days apart. |
| **C — bridge node** | Largest component 630 nodes. Removing the bridge splits it **316 / 313 — a 50/50 halving.** |

Scenario entities carry an `attributes["scenario"]` marker (`A_center`, `A_member`,
`B_record_a`, `B_record_b`, `C_bridge`) so `--verify` and the demo can find them.
First version looked them up by `source_ref` prefix, which was wrong: a person's
prefix depends on a random agency draw, so the lookup would have silently missed.

**Agency scoping is visible in the data — the S2 mechanism**

| login | role | agency | entities | relationships |
|---|---|---|---|---|
| `investigator` | investigator | GJ_POLICE | 402/650 | 616/940 |
| `admin` | admin | GJ_POLICE | **650/650** | **940/940** |
| `telecom_officer` | investigator | TELECOM | 217/650 | 188/940 |
| `rto_officer` | investigator | RTO | 191/650 | 136/940 |

80 of 650 entities are `is_shared`. Persons are split 225 police / 40 RTO owner
records / 38 telecom subscriber records — that cross-agency overlap is what makes
entity resolution meaningful rather than a toy.

**Deliberate noise, per the PRD risk table**
61 persons with no alias, 29 with no address, 20 entities with no edges at all.

**All six logins verified** — correct password accepted, wrong password rejected.
Password is the username followed by `123`.

**`backend/dev_users.py` deleted.** Its own docstring said to remove it when
`seed.py` landed. `seed.py` keeps the same `investigator` / `admin` usernames and
passwords, so nothing that relied on it breaks. `auth.py` had one docstring line
naming it; that now says `seed.py`. Logged as a shared-file change.

**Not done, and why**
- **The ~0.85 score for Scenario B is not asserted.** `resolution.py` does not
  exist yet, so there is no scorer to run. `--verify` checks the *structural*
  preconditions instead — close names, shared phone, shared location, DOBs two days
  apart. I will assert the actual score in W3 F8a and tune the weights then.
- `seed.py` is **487 lines**, over the ~300 guideline in `CLAUDE.md` §4. Most of it
  is static name pools and the three scenario builders. Splitting the pools into a
  sibling module would fix it but adds a file not in §4. Flagging rather than
  deciding alone.

**Files touched**
- `backend/seed.py` (new), `backend/dev_users.py` (deleted),
  `backend/app/auth.py` (one docstring line), `PROGRESS.md`

**Next**
- W3 F8a `resolution.py` scoring, or my three router stubs
  (`routers/audit.py`, `resolution.py`, `query.py`) which Krish left for me.

**For Krish**
- **Run `python seed.py --reset --verify` and compare the digest above.**
- **`python dev_users.py` no longer exists** — `seed.py` replaces it, same two
  logins, plus four more. Your notes still say to run it.
- **`dev_data.py` should go when your chain merges.** `seed.py` gives you a real
  630-node component instead of 12 fake records, and your `/api/graph` will finally
  return something. Your F3a exit criterion can be re-measured on real data.
- **I agree with your relationship-scoping call** — entities on `agency_id` OR
  `is_shared`, relationships on `agency_id` alone. A shared node appearing with no
  edges is correct: knowing a phone exists is not knowing who called it. It is also
  a good viva answer. Seeded data exercises it — 80 shared entities.
- **`.env.example` still says 5432 and we both hit the clash.** Two for two, so I
  will flip it to 5433 with a comment unless you object.
- Your `ResolutionFeature` shape looks fine; I will confirm when F8a lands.

---

### 2026-09-28 · W1-4 auth.py · `phase-2-auth-rishabh`

Branched off `phase-0-scaffold-rishabh`, **not** off `main`, because `models.py` and
`database.py` are still on that unmerged branch. Stacked deliberately rather than
self-merging the scaffold: the Decisions log wants PRs landing on both GitHub
profiles, and merging my own work would throw that record away. Once Krish reviews
and merges the scaffold PR, this rebases onto `main`.

**Done**
- `auth.py` — `hash_password`, `verify_password`, `create_access_token`,
  `decode_token`, `get_current_user`, `require_admin`. `bcrypt.hashpw` /
  `bcrypt.checkpw` directly and PyJWT, per the rejected-technology table. Installed
  bcrypt is 5.0.0, which is exactly the version family that breaks `passlib`.
- `routers/auth.py` — `POST /api/auth/login` (OAuth2 form body, per §6) and
  `GET /api/auth/me`.
- `schemas.py` — **only** `UserOut`, `LoginRequest`, `TokenResponse`.
- `main.py` — two lines: import and `include_router`.
- `dev_users.py` — one agency, two users, idempotent. Temporary; delete when
  `seed.py` lands.

**Verified — 18/18, against the live server**

| Criterion | Result |
|---|---|
| login returns a token | `POST /api/auth/login` → 200, `access_token`, `token_type: bearer`, embedded user |
| `/auth/me` returns the user | 200, username + role + `agency_code` GJ_POLICE + agency name |
| missing token → 401 | `{"detail":"Not authenticated"}` |
| malformed token → 401 | `{"detail":"invalid token"}` |
| expired token → 401 | `{"detail":"token has expired"}` |
| token signed with wrong secret → 401 | `{"detail":"invalid token"}` |
| `require_admin` → 403 for investigator | `403: this action requires the admin role` |
| `require_admin` passes an admin | returns the user unchanged |
| wrong password → 401 | same message as unknown username |
| unknown username → 401 | identical message, so valid usernames are not disclosed |

`require_admin` is verified at the function level, not over HTTP, because no
admin-only route exists yet — the first is `POST /entities` in W1-7. Worth
re-checking over HTTP once that exists.

**Decisions**
- `get_current_user` re-reads the `User` row on every request rather than trusting
  the JWT claims, so a user deleted or moved to another agency cannot keep acting on
  a still-valid token. Costs one indexed primary-key lookup per request.
- Login returns an identical 401 for a bad password and an unknown username, so the
  endpoint is not a username oracle.
- `verify_password` catches `ValueError` and returns `False`. bcrypt rejects
  passwords over 72 bytes rather than truncating them, and a long password is a
  failed login, not a 500.
- The token carries `agency_id` as a claim, but scoping code should read it from the
  `User` row, not the claim, for the same staleness reason.

**Files touched**
- `backend/app/auth.py` (new), `backend/app/routers/auth.py` (new),
  `backend/app/schemas.py` (new), `backend/app/main.py` (+2 lines),
  `backend/dev_users.py` (new), `.env.example` (comment), `PROGRESS.md`

**Next**
- W1-5 `audit.py` — hash chain and its pytest. Same branch or a new one.

**For Krish**
- **`schemas.py` now exists with three auth models. W1-6 should ADD the remaining
  ~17 to it, not recreate the file** — recreating it would drop `UserOut`,
  `TokenResponse` and `LoginRequest` and break login. Import `ENTITY_TYPES`,
  `USER_ROLES` and `RESOLUTION_STATUSES` from `models.py` rather than repeating the
  literals.
- `main.py` mounts routers with `app.include_router(...)` after the CORS block. Add
  yours the same way.
- For any protected route: `user: User = Depends(get_current_user)`, and
  `Depends(require_admin)` for admin-only. `POST /entities` is the first that needs
  the admin one.
- Login credentials for testing are in `backend/dev_users.py`. Run
  `python dev_users.py` once after `init_db()`.
- `.env.example` now notes that `JWT_SECRET` needs 32+ bytes — the old placeholder
  was short enough to make PyJWT warn on every token.

---

### 2026-09-28 · W1-2 + W1-3 · `phase-0-scaffold-rishabh`

Took these two although KICKOFF suggests Krish, because they are the critical path
and he has not started. Neither touches a file he exclusively owns: `models.py` and
`main.py` are **"Shared — protocol required"** in the ownership table, and
`config.py` / `database.py` sit under *"Built jointly in Week 1"* in `PRD.md` §11.
Claimed in `PROGRESS.md` and pushed to `main` before writing any code.

**Done — W1-2**
- `requirements.txt` — the 13 packages in `CLAUDE.md` §3, nothing added
- `config.py` — pydantic-settings; resolves `.env` from `__file__`, not the working
  directory, so uvicorn, pytest and `python -c` all read the same file
- `database.py` — `engine`, `SessionLocal`, `get_db`, `Base`, `init_db()`
- `main.py` — CORS for `http://localhost:5173`, `GET /api/health`
- `.venv` created, all 13 installed

**Done — W1-3**
- All six tables. One `entities` table with `attributes` JSONB; no table per type
- The five indexes W1-3 names: `entities.entity_type`, `entities.agency_id`,
  `relationships.src_entity_id`, `.dst_entity_id`, `.valid_from`
- `audit_log.seq` unique
- CHECK constraints on `users.role`, `entities.entity_type`,
  `resolution_candidates.status`, built from module-level tuples so the allowed
  values and the constraints cannot drift
- `UniqueConstraint` on `(entity_a_id, entity_b_id)` — makes F8's *"a rejected pair
  is never re-proposed"* structural rather than a code convention

**Two schema decisions that matter — read these**

1. **`audit_log.timestamp` is a naive `DateTime` with no server default.** The hash
   payload embeds `timestamp.isoformat()`, so `verify_chain` has to recompute a
   byte-identical string. A `server_default` would mean the value in the hash was
   never the value Postgres stored. A `timestamptz` can come back rendered in a
   different session timezone on the other machine. Either one silently breaks the
   chain — on the one feature whose failure is invisible on screen. `audit.py` sets
   this value in Python, in UTC. Everything else uses `timestamptz` + `now()`.
2. **The relationship foreign keys do not cascade on delete.** Confirming a
   resolution candidate rewires B's edges onto A and then removes B, so B should own
   no edges by then. Without cascade, a bug in that rewiring raises a foreign-key
   error instead of quietly destroying edges.

**Verified**
- `python -c "from app.database import init_db; init_db()"` — ran clean
- `psql \dt` — exactly 6 tables: `agencies`, `audit_log`, `entities`,
  `relationships`, `resolution_candidates`, `users`
- `psql \di` — all five required indexes present
- `uvicorn app.main:app --reload` — clean startup, no warnings
- `GET /api/health` → HTTP 200, `{"status":"ok","db":"connected"}` — a real
  `SELECT 1` against Postgres, matching the W1-2 criterion exactly
- CORS preflight from `http://localhost:5173` → 200, correct `allow-origin`
- All six tables compile to valid Postgres DDL (checked via the mock dialect
  before the container existed)

**Machine-local deviation — Postgres is on port 5433 here, not 5432**

This machine already runs a native Windows **PostgreSQL 18** service
(`postgresql-x64-18`) bound to 5432. Docker reported the container as published on
5432, but `localhost:5432` rejected the password `crimenet`, which proved the native
service owned the port and the container was shadowed. Rather than stop a service
that probably belongs to another project, the container is published on **5433**:

```
docker run --name crimenet-db -e POSTGRES_PASSWORD=crimenet \
  -e POSTGRES_DB=crimenet -p 5433:5432 -d postgres:16
```

Only my local `.env` points at 5433. **`.env.example` is deliberately left at 5432**
because this is a conflict on my machine, not a project-wide change. Confirmed we
reach the container by checking `server_version` is 16.15 and not 18.

**Files touched**
- `backend/requirements.txt` (new), `backend/app/config.py` (new),
  `backend/app/database.py` (new), `backend/app/main.py` (new),
  `backend/app/models.py` (new), `PROGRESS.md` (rows + shared-file log)

**Next**
- **W1-4 `auth.py` is now unblocked.** W1-5 `audit.py` too.

**For Krish**
- **Reseed needed.** Pull, then
  `python -c "from app.database import init_db; init_db()"`.
- `models.py` is a shared file and it now exists. Read the two decisions above
  before changing anything in it; both exist to stop the audit chain breaking
  silently. Any change follows the §6 schema protocol.
- `W1-6 schemas.py` and `W1-7 router stubs` are unclaimed and now unblocked —
  `models.py` and `database.py` are in place. Those are the natural next ones for
  you. Import the allowed-value tuples from `models.py` (`ENTITY_TYPES`,
  `USER_ROLES`, `RESOLUTION_STATUSES`) rather than repeating the literals.
- `main.py` has no router mounts yet — nothing exists to mount. Add yours as you go.
- Installed versions worth knowing: SQLAlchemy 2.1.1, psycopg 3.3.6, FastAPI 0.141.1,
  pydantic 2.13.5, **bcrypt 5.0.0**, PyJWT 2.15.0, NetworkX 3.7, pandas 3.0.6.
  bcrypt is 5.x, which is exactly why `CLAUDE.md` rules out `passlib` — I will use
  `bcrypt.hashpw` / `checkpw` directly in W1-4.
- Still outstanding: `pytest` is not in §3 but W1-5 needs `tests/test_audit.py`.

---

### 2026-09-27 · directory skeleton · committed to `main`

**Done**
- Created `backend/app/`, `backend/app/routers/`, `backend/tests/`
- `backend/app/__init__.py` and `backend/app/routers/__init__.py` — empty, but
  genuinely required rather than placeholders: without them `from app.main import
  app` and `from app.routers import auth` do not resolve
- `backend/tests/.gitkeep` so the directory survives a commit; it goes away when
  `test_audit.py` lands in W1-5
- `CLAUDE.md` Section 4 tree: added `analysis.py`, `backend/tests/test_audit.py`,
  `pages/Stats.jsx` and `components/AnalysisPanel.jsx`. All four appear in the
  `PRD.md` Section 11 ownership table and in the ownership block at the top of
  `CLAUDE.md`, but were absent from the tree — so the documented layout
  contradicted the ownership map.

**Deliberately not done**
- **No `frontend/` directory.** `npm create vite@latest frontend` in W1-8 refuses
  to scaffold into a non-empty directory without prompting to delete its contents,
  so pre-creating `frontend/src/...` would actively get in the way. Vite creates it.
- No `requirements.txt`, `config.py`, `database.py`, `main.py`, `models.py` or
  `schemas.py`. Those are W1-2 and W1-3, Krish's tasks. Only the directories and
  the two package `__init__.py` files exist.
- No `seed.py`, `resolution.py`, `analysis.py` or `llm.py`. Mine, but W2 onward.
- No service layer, no repository pattern, no `core/` or `utils/` package. The flat
  layout in `CLAUDE.md` Section 4 is the structure, per Section 2.

**Verified**
- `git diff --stat CLAUDE.md`: 6 insertions, 1 deletion — the deletion being the
  `AuditLog.jsx` connector changing from last-child to mid-child. Nothing outside
  the Section 4 tree was touched.
- Tree renders with correct box-drawing alignment (first attempt corrupted the
  prefixes because these lines start with `│`, not whitespace; reverted via
  `git checkout` and redone)

**Files touched**
- `CLAUDE.md` (Section 4 tree only), `PROGRESS.md` (shared-file log),
  `backend/app/__init__.py` (new), `backend/app/routers/__init__.py` (new),
  `backend/tests/.gitkeep` (new)

**Next**
- Still blocked on W1-2 and W1-3 before W1-4 `auth.py` can start.

**For Krish**
- `backend/app/` and `backend/app/routers/` already exist with `__init__.py`.
  **W1-2 and W1-3 are otherwise untouched** — every file those tasks list is still
  yours to write.
- I made a small edit to the `CLAUDE.md` Section 4 tree, logged in `PROGRESS.md`.
  Pull before you touch that file.
- There is no `frontend/` directory yet, on purpose — see above.

---

### 2026-09-27 · W1-1 repo bootstrap · committed directly to `main`

**Done**
- `git init -b main`, `origin` → `github.com/rishabhxnandekar21/Nexus`
- `.gitignore` written before the first commit, as specified
- Committed the five documents, a `README.md` stub, and `.env.example`
- Created `progress/krish.md` and `progress/rishabh.md`
- Pasted the `TEAM-WORKFLOW.md` Section 2 block — the session-start checklist and
  the file-ownership table — into the top of `CLAUDE.md`, above Section 1. It had
  only ever existed as a "paste this" snippet inside `TEAM-WORKFLOW.md`, so no
  session was actually reading it. Extracted programmatically from the source file
  rather than retyped, so it is byte-identical.
- Corrected the repo name to `Nexus` in `PRD.md` (was codename `kadi`) and in the
  `CLAUDE.md` Section 4 tree (was rooted at `crimenet/`). The **database** name
  `crimenet` is deliberately untouched — it appears in `DATABASE_URL`, the Docker
  container name, and `POSTGRES_DB`, and none of those changed.

**Verified**
- `git ls-remote` on the remote returned zero refs before this commit, so nothing
  was overwritten
- `git status` clean after commit; `.env` correctly ignored (tested with a scratch
  `.env`, which git did not see)
- All seven documents present and non-empty on disk

**Files touched**
- `.gitignore` (new), `CLAUDE.md` (new, + pasted block), `PRD.md` (new, name fix),
  `TEAM-WORKFLOW.md` (new, unchanged from source), `PROGRESS.md` (new, W1 row
  claimed + shared-file log line), `KICKOFF.md` (new), `README.md` (new),
  `.env.example` (new), `progress/krish.md` (new, heading only),
  `progress/rishabh.md` (new)

**Next**
- Blocked. W1-4 `auth.py` needs `config.py` + `database.py` (W1-2) and the `users`
  and `agencies` tables (W1-3). W1-5 `audit.py` needs the `audit_log` table (W1-3).
  Nothing in my lane starts until those land.

**For Krish**
- **The repo is `Nexus`**, not `kadi` and not `crimenet`. Docs now say so.
- W1-1 went straight to `main` — there was no commit to branch from and no PR
  target. Everything from here follows the normal branch + PR flow.
- **W1-2 and W1-3 are unclaimed and are the critical path.** Both of my first two
  tasks are blocked behind them. Please take them next rather than W1-6 or W1-7.
- `pytest` is **not** in the `CLAUDE.md` Section 3 dependency list, but W1-5 (mine)
  requires `tests/test_audit.py` and Section 8 explicitly asks for that one test.
  I will need to add `pytest` to `requirements.txt`. Flagging per
  `TEAM-WORKFLOW.md` Section 5.4 — dependencies get added in foundation week, in
  their own commit. Shout if you object.
- My Python is 3.13.12. If yours is meaningfully different, worth knowing now,
  since `seed.py` has to produce identical output on both machines in Week 2.
