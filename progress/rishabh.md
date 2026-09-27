# Rishabh — Session Log

> Only Rishabh writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

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
