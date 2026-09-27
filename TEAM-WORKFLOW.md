# Team Workflow — Two People, Two Claude Code Sessions, One Repo

> Krish and Rishabh each run their own Claude Code session on their own machine.
> Neither session can see the other's memory, terminal, or uncommitted files.
> **The git repo is the only communication channel between them.**
> Everything in this file exists to make that channel reliable.

---

## 1. The three failure modes this prevents

**Invisible work.** Claude only knows what is committed *and pushed*. Three days
of uncommitted work on Rishabh's machine does not exist as far as Krish's session
is concerned, and it will cheerfully rebuild the same thing. → Push daily,
without exception.

**Cross-editing.** Claude will confidently "improve" code it did not write —
renaming functions, restructuring routers, reformatting components. Two Claudes
doing this in alternating sessions is a worse problem than merge conflicts,
because git resolves cleanly and the damage is silent. → Ownership map, enforced
in `CLAUDE.md`.

**Silent schema drift.** No migrations means a `models.py` change breaks the other
person's database with no warning. → Schema-change protocol, Section 6.

---

## 2. Add this to `CLAUDE.md`

Paste this block at the very top of `CLAUDE.md`, above Section 1. Claude Code
reads `CLAUDE.md` automatically; it does not read `PROGRESS.md` unless told to.
Without this block the whole handoff system is just a file nobody opens.

```markdown
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
```

---

## 3. Repo layout for coordination

```
PROGRESS.md              # phase status table + shared-file log + requests
progress/
  ├── krish.md           # Krish's session log — only Krish writes here
  └── rishabh.md         # Rishabh's session log — only Rishabh writes here
```

Two authors, two files, so the detailed logs can never conflict. `PROGRESS.md`
changes rarely — roughly once per phase per person — and each person edits only
their own rows.

---

## 4. The daily cycle

### Starting a session

```bash
git checkout main
git pull --rebase
git checkout -b phase-3-graph-krish
```

Then open Claude Code. It reads `CLAUDE.md`, follows the session-start block, and
reports back what it found before writing anything. **Read that report.** It is
your check that Claude actually understood the current state rather than
inventing it.

### Branch naming

```
phase-<N>-<short-feature>-<yourname>
```

`phase-3-graph-krish`, `phase-5-resolution-rishabh`, `schema-add-alias-field-krish`.

### Ending a session

```bash
# 1. verify (example)
python seed.py --verify
pytest tests/test_audit.py

# 2. Claude appends to progress/krish.md, updates PROGRESS.md row

# 3. commit and push
git add -A
git commit -m "phase-3: graph endpoint with agency scoping and date filters"
git push -u origin phase-3-graph-krish
```

**Push every single day you write code**, even mid-feature, even broken. A
pushed broken branch is visible and recoverable. Unpushed work is invisible and
gets duplicated.

### Merging

Open a PR when the phase's exit criteria pass. The other person skims it — five
minutes, not a formal review — and merges. Then both run:

```bash
git checkout main && git pull --rebase
```

**No branch lives longer than three days.** If a feature needs more, split it and
merge the first half.

---

## 5. Rules that keep `main` working

1. **`main` must always run.** If you push something to main that breaks startup,
   fix it or revert within the hour. The other person's Claude session will pull
   it and try to "fix" imaginary problems.
2. **Always `git pull --rebase`**, never a plain pull. Merge commits from two
   people on a small repo make the history unreadable, and unreadable history is
   exactly what a Claude session needs in order to understand progress.
3. **Never commit** `.env`, `node_modules/`, `__pycache__/`, `*.db`, or seed
   output. `.gitignore` goes in before the first commit, not after.
4. **Dependencies are added in foundation week.** After that, adding one needs a
   message to your teammate first. Whoever adds it commits the updated
   `requirements.txt` or `package-lock.json` in its own commit, alone.
5. **On a `package-lock.json` conflict**, do not hand-merge. Take `main`'s
   version, re-run `npm install`, commit the result.

---

## 6. Schema-change protocol

Because there are no migrations, a `models.py` change is a breaking change for
the other person's database. Every schema change follows these five steps.

1. **Propose.** Add an entry under *Shared-file changes* in `PROGRESS.md`:
   what column, which table, why.
2. **Tell your teammate directly.** WhatsApp, not the file. The file is the
   record; the message is the notification.
3. **Branch alone.** `schema-<what>-<yourname>`, containing only the `models.py`
   change and the matching `seed.py` update. Nothing else.
4. **Merge same day.** Schema branches never sit overnight.
5. **Both reseed.** Everyone runs `git pull --rebase && python seed.py --reset`
   before their next session.

If you are mid-feature when a schema change lands, commit your work first, then
pull and reseed.

---

## 7. `PROGRESS.md` structure

Three sections, each with a conflict-avoidance rule.

**Phase status table** — one row per phase. Only the phase owner edits their own
row. Changes roughly once per phase.

**Shared-file changes** — append-only. Every change to `models.py`,
`schemas.py`, `main.py`, `requirements.txt` or `package.json` gets one line, newest
at the bottom. This is what a Claude session reads to understand why something it
remembers has changed shape.

**Open requests and blockers** — two fixed subsections, one per person. You write
only under your own heading. A request is how you ask for a change in a file you
do not own.

The starter file is in `PROGRESS.md`, ready to commit.

---

## 8. Session log entry format

In `progress/<yourname>.md`, newest entry at the top:

```markdown
### 2026-10-07 · phase-3-graph-krish

**Done**
- GET /api/graph with center, depth, from, to, types
- Agency scoping in build_graph(); admin bypasses the filter
- Cytoscape element serialization

**Verified**
- Investigator token: 47 nodes. Admin token: 118 nodes. Scoping confirmed.

**Files touched**
- app/graph.py (new), app/routers/graph.py, app/schemas.py (added GraphResponse)

**Next**
- GraphView.jsx rendering; node colour by type

**For Rishabh**
- build_graph(db, user, center_id, depth, date_from, date_to, types) -> nx.Graph
  is stable now. Call it from analysis.py; do not edit graph.py.
- I added GraphResponse to schemas.py — pull before you touch that file.
```

That last section is the one that matters. It is what the other Claude session
reads to learn what changed underneath it.

---

## 9. What to keep in mind

**Foundation week is the whole game.** Every hour spent in Week 1 agreeing on
`models.py` and `schemas.py` saves roughly a day of conflict later. Sit together
for it, physically if you can, with one screen.

**Read Claude's opening report.** Both sessions will start by claiming to
understand the project state. When that report is wrong, stop and correct it
before any code gets written. A session that starts from a wrong mental model
produces work that looks right and integrates badly.

**Commit small and often.** A commit per logical change, not per day. When two
branches touch adjacent code, small commits rebase cleanly and large ones do not.

**Demo before generality, always.** If you catch either Claude building
configurable, extensible, or reusable versions of things, stop it. You have seven
weeks and one demo.

**Test the tamper demo early and repeatedly.** The audit chain is the single
feature where a silent bug destroys the claim entirely, and you will not notice
by looking at the screen. That is why it is the one thing with a pytest.

**Rehearse the demo on the actual machine.** Three full runs in Week 7, no fixes
between runs. Most demo failures are environment failures, not code failures.

**Neither of you should own only the invisible parts.** If one of you ends up
having built nothing on screen, the viva goes badly for that person regardless of
how much they contributed. The ownership map is built to prevent this — keep it
that way if you rebalance.
