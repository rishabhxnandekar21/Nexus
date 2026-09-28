# Krish — Session Log

> Only Krish writes in this file. Newest entry at the top.
> Entry format is in `TEAM-WORKFLOW.md` Section 8.

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
