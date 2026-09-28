# PROGRESS

> **Read this before writing any code.** It is the handoff channel between two
> people working on two machines with two separate Claude Code sessions.
>
> **Editing rules**
> - Phase table: edit **only your own rows**.
> - Shared-file changes: **append only**, newest at the bottom.
> - Requests and blockers: write **only under your own heading**.
> - Detailed session notes do not go here — they go in `progress/krish.md` or
>   `progress/rishabh.md`.

**Current phase:** Week 1 — Foundation (both)
**Last updated:** 2026-09-29

---

## Phase status

| Phase | Feature | Owner | Status | Branch | PR | Verified |
|---|---|---|---|---|---|---|
| W1 | Repo, scaffold, Docker Postgres | Both | ✅ done | phase-0-scaffold-rishabh | #1 | `/api/health` ok, db connected |
| W1 | `models.py` — all six tables | Both | ✅ done | phase-0-scaffold-rishabh | #1 | 6 tables + 5 indexes in psql |
| W1 | `auth.py` — JWT + roles | Both | ✅ done | phase-2-auth-rishabh | #1 | 18/18 checks: login, /me, 401s, 403 |
| W1 | `audit.py` — hash chain + pytest | Both | 🔵 in review | w1-5-audit-krish | — | 7/7 pytest; tamper detected at exact seq |
| W1 | `schemas.py` — all contracts | Both | 🔵 in review | w1-6-schemas-krish | — | 34 models; 26 now in /docs, 8 await Rishabh's routers |
| W1 | Router stubs returning fake data | Both | 🔵 in review | w1-7-stubs-krish | — | Krish's 8 routes live; 16/16 checks incl. 403 |
| W1 | Frontend shell, AuthContext, login | Both | 🔵 in review | w1-8-frontend-krish | — | login, nav badges, refresh, logout - all live |
| W2 | F7 `seed.py` + 3 scenarios | Rishabh | ⬜ not started | — | — | — |
| W2 | F3a `graph.py` + `/api/graph` | Krish | 🔵 in review | w2-graph-krish | — | 25/25 pytest; S2 asserted on test rows |
| W3 | F3b GraphView, panel, search | Krish | ⬜ not started | — | — | — |
| W3 | F8a resolution scoring + endpoints | Rishabh | ⬜ not started | — | — | — |
| W3 | F2 audit log page + verify button | Rishabh | ⬜ not started | — | — | — |
| W4 | F8b resolution review UI + merge | Rishabh | ⬜ not started | — | — | — |
| W4 | F5 analytics + community colouring | Krish | ⬜ not started | — | — | — |
| W5 | F6 timeline slider + play | Krish | ⬜ not started | — | — | — |
| W5 | F9 what-if + link prediction | Rishabh | ⬜ not started | — | — | — |
| W6 | F10 LLM query + brief + cache | Rishabh | ⬜ not started | — | — | — |
| W6 | Integration, loading/empty/error states | Krish | ⬜ not started | — | — | — |
| W7 | Freeze, README, rehearsal, deck | Both | ⬜ not started | — | — | — |

Status values: ⬜ not started · 🟡 in progress · 🔵 in review · ✅ done

---

## Demo criteria — the real definition of done

| # | Criterion | Owner | Proved? |
|---|---|---|---|
| S1 | Multi-source data appears as one graph | Krish | ⬜ |
| S2 | Two logins → two visibly different graphs | Krish | ⬜ |
| S3 | Duplicate proposed, human-confirmed, nodes merge on screen | Rishabh | ⬜ |
| S4 | Tampered audit row → `/audit/verify` reports the exact seq | Rishabh | ⬜ |
| S5 | Timeline replays growth; bridge removal splits the graph | Both | ⬜ |

---

## Shared-file changes

Append one line for every change to `models.py`, `schemas.py`, `main.py`,
`requirements.txt` or `package.json`. Newest at the bottom. Never edit or delete
an existing line.

| Date | Who | File | Change | Reseed needed? |
|---|---|---|---|---|
| 2026-09-25 | Both | — | Repo created, foundation week begins | — |
| 2026-09-27 | Rishabh | docs | W1-1 bootstrap. Repo is `Nexus` (not `kadi`/`crimenet`) - name corrected in PRD.md and the CLAUDE.md tree. TEAM-WORKFLOW section 2 block pasted into CLAUDE.md as instructed. | no |
| 2026-09-27 | Rishabh | CLAUDE.md | Section 4 tree only: added `analysis.py`, `backend/tests/test_audit.py`, `pages/Stats.jsx`, `components/AnalysisPanel.jsx`. All four are in the PRD Section 11 ownership table but were missing from the tree. Also created `backend/app/` and `backend/app/routers/` with empty `__init__.py`. | no |
| 2026-09-28 | Rishabh | requirements.txt, models.py, main.py | W1-2 + W1-3. `requirements.txt` = the 13 deps in CLAUDE.md Section 3, nothing added. New `config.py`, `database.py` (Base, engine, SessionLocal, get_db, init_db), `main.py` (CORS for :5173 + GET /api/health), `models.py` (all six tables, the five required indexes, CHECK constraints on role/entity_type/status). | yes - run `python -c "from app.database import init_db; init_db()"` |
| 2026-09-28 | Rishabh | schemas.py, auth.py, main.py, .env.example | W1-4. New `auth.py` (bcrypt direct + PyJWT, `get_current_user`, `require_admin`). New `schemas.py` with ONLY `UserOut`, `LoginRequest`, `TokenResponse` - **W1-6 should add the remaining ~17 models to this file, not recreate it.** `main.py` gained two lines mounting the auth router. `.env.example` gained a comment about minimum JWT_SECRET length. | no |
| 2026-09-29 | Krish | schemas.py | W1-6. Added 31 models to `schemas.py`, 34 total - every contract in CLAUDE.md Section 6. Rishabh's three auth models are untouched. `EntityType`/`UserRole`/`ResolutionStatus` are StrEnums derived from the tuples in `models.py`, used on requests only. Cytoscape ids are strings, deliberately. `ResolutionFeature` and `NLQueryFilters` are proposed shapes for Rishabh's JSONB and LLM filters - his to change. | no |
| 2026-09-29 | Krish | main.py | W1-7. `main.py` gained 3 lines: `entities` and `graph` added to the routers import, and two `include_router` calls. Nothing else in that file touched. New `routers/entities.py` and `routers/graph.py` are stubs over 12 fake records - no database access. **Not audited**: `audit.py` does not exist yet (W1-5), so the stub routes are protected but not logged. Must be revisited when W1-5 lands. | no |
| 2026-09-29 | Krish | package.json | W1-8. New `frontend/package.json`. **React pinned to 18**, not the 19 the Vite template now ships: `CLAUDE.md` Section 3 says React 18, and `react-cytoscapejs` 2.0.0 does not declare React 19 support - that is Krish's W3 graph canvas, so it is not worth the risk. Vite 8, Tailwind v4 via `@tailwindcss/vite` with no config file, plus `react-router-dom`, `axios`, `cytoscape`, `react-cytoscapejs`. Nothing beyond the Section 3 list. | no |
| 2026-09-29 | Krish | requirements.txt | W1-5. Added `pytest`, in its own commit per TEAM-WORKFLOW 5.4. Answers Rishabh's W1-4 question - CLAUDE.md Section 8 requires `tests/test_audit.py`, so it was implied by the plan even though Section 3 omits it. | no |
| 2026-09-29 | Krish | audit.py | W1-5. New shared `app/audit.py`: `compute_hash`, `write_audit`, `verify_chain`, `chain_length`, and an `audited()` route dependency. Payload string is CLAUDE.md Section 5 verbatim. `write_audit` flushes but does not commit - the caller owns the transaction. My 8 W1-7 routes now use `audited(...)` in place of `get_current_user`. **`routers/audit.py` is untouched and still Rishabh's**, so `GET /api/audit` and `/api/audit/verify` do not exist yet. | no |
| 2026-09-29 | Krish | CLAUDE.md | Team name in Section 1 changed from `Delulu Developers` to `Apostrophe`, to match Rishabh's README edit of 27 Sep. The two documents had disagreed since then. | no |
| 2026-09-29 | Krish | graph.py, routers/graph.py | W2 F3a. New `app/graph.py` with `build_graph()`, `can_see_entity()` and `to_cytoscape()`. `GET /api/graph` now reads Postgres instead of the fake set - **it returns an empty graph until `seed.py` runs, which is correct, not a failure.** The other four graph routes and all of `routers/entities.py` are still stubs. | no |

---

## Open requests and blockers

A request is how you ask for a change in a file you do not own. Write only under
your own heading. Delete your own entries once resolved.

### From Krish

- **`pytest` is not in `requirements.txt`.** You flagged this twice and I never
  answered - sorry. Yes, add it. `CLAUDE.md` Section 8 requires
  `tests/test_audit.py`, so the dependency is already implied by the plan. Its own
  commit, per Section 5.4.
- **Who stubs `routers/audit.py`, `routers/resolution.py` and `routers/query.py`?**
  W1-7 says "every endpoint", but those three are yours in the ownership table and
  routers are not in the `PRD.md` Section 11 "built jointly in Week 1" list. I am
  doing `routers/graph.py` and `routers/entities.py` only and will not touch the
  other three until we agree.
- **`.env.example` should probably move to 5433.** You left it at 5432 because the
  native-Postgres clash looked machine-local. It is not - this machine runs
  `postgresql-x64-17` on 5432 and hit exactly the same shadowing. Both of us are
  now on 5433, so the committed example is the odd one out. Your call, it is your
  find.

### From Rishabh

*(none)*

---

## Decisions log

Short, permanent record of choices made mid-build, so neither Claude session
re-litigates them.

| Date | Decision | Reason |
|---|---|---|
| 2026-09-25 | Local Postgres per machine, deterministic seed | Shared DB would let one person's reseed wipe the other's session |
| 2026-09-25 | Hybrid split: foundation together, then vertical ownership | Removes the conflict surface once instead of managing it for six weeks |
| 2026-09-25 | Short-lived phase branches + PR, max 3 days | Keeps `main` green; puts PRs on both GitHub profiles |
| 2026-09-25 | `build_graph()` in `graph.py` is the interface between graph and analysis | Lets Rishabh build analytics without editing Krish's files |
