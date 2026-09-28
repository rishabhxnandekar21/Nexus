# Krish — Session Log

> Only Krish writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

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
