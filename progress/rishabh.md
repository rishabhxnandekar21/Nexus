# Rishabh — Session Log

> Only Rishabh writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

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
