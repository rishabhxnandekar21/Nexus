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
**Last updated:** 2026-09-28

---

## Phase status

| Phase | Feature | Owner | Status | Branch | PR | Verified |
|---|---|---|---|---|---|---|
| W1 | Repo, scaffold, Docker Postgres | Both | 🔵 in review | phase-0-scaffold-rishabh | — | `/api/health` ok, db connected |
| W1 | `models.py` — all six tables | Both | 🔵 in review | phase-0-scaffold-rishabh | — | 6 tables + 5 indexes in psql |
| W1 | `auth.py` — JWT + roles | Both | ⬜ not started | — | — | — |
| W1 | `audit.py` — hash chain + pytest | Both | ⬜ not started | — | — | — |
| W1 | `schemas.py` — all contracts | Both | ⬜ not started | — | — | — |
| W1 | Router stubs returning fake data | Both | ⬜ not started | — | — | — |
| W1 | Frontend shell, AuthContext, login | Both | ⬜ not started | — | — | — |
| W2 | F7 `seed.py` + 3 scenarios | Rishabh | ⬜ not started | — | — | — |
| W2 | F3a `graph.py` + `/api/graph` | Krish | ⬜ not started | — | — | — |
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

---

## Open requests and blockers

A request is how you ask for a change in a file you do not own. Write only under
your own heading. Delete your own entries once resolved.

### From Krish

*(none)*

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
