# Blood Bank Dispatch

A phone agent that finds blood stock fast. A clinic files one request — blood
group, rhesus, units needed — and the agent dials every blood bank in
parallel, asks a fixed set of questions, and returns a ranked shortlist of who
has the units and how fast they can reach the patient. A serial 20-minute
manual calling process becomes a parallel 90-second one.

Built on the [CALL-E](https://docs.heycall-e.com/) phone-call API for the
CALL-E hackathon.

> **Decision support only.** This agent gathers and reports. It never makes a
> clinical decision, never reserves, never dispatches, and never promises
> anything on anyone's behalf. A qualified human reads the shortlist and acts.

> **Demo disclosure.** All demo targets are mock lines. No real blood bank is
> called. The mock spread (stock, no-stock, hold, callback-requested) exists
> to prove the extraction schema survives messy conversations, not just a
> happy path.

## What it does

1. Operator keeps a registry of blood banks (name, E.164 phone, area, notes).
2. Operator files a request: group, rhesus, units, which banks to call, plus
   optional ad hoc numbers.
3. Every target is inserted into `call_results` as `queued` **before** any
   call is placed — the UI shows all cards immediately.
4. The backend fans out one CALL-E call per target (`asyncio.gather` +
   semaphore), asking an ordered set of questions: units available, screening
   and cross-match status, release policy, cost per unit, transport time,
   contact person, alternatives.
5. Each answer is extracted into a strict JSON schema (`unknown` enum members
   preserve hedged answers as real information) and persisted alongside the
   raw CALL-E response and transcript.
6. The results page polls every two seconds; cards transition `queued →
   dialing → terminal`, and a shortlist ranks completed results by units
   available, then time to bedside.

## What it deliberately does not do

- No reservations, orders, or commitments — the task prompt forbids it, and
  the agent is instructed to defer any confirmation to a human callback.
- No patient names — `patient_ref` is an opaque internal string, and the UI
  never collects one.
- No clinical recommendations — output is a shortlist for a qualified human.
- No emergency handling — this tool is for planned stock checks, not urgent
  clinical escalation, which belongs to local emergency protocols.

## Quick start

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # or: fastapi uvicorn jinja2 asyncpg python-multipart python-dotenv calle-ai

copy .env.example .env        # then fill in CALLE_API_KEY and DATABASE_URL

python migrate.py             # applies migrations/*.sql
python seed.py                # four fictional demo banks

venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Open `http://localhost:8000` → New request.

A run costs one paid CALL-E call per target. Test with single-target runs
while building; save full fan-outs for integration checks and recording.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `CALLE_API_KEY` | yes | — | CALL-E API key (`iams_live_...`). Server side only; the browser gets htmx and HTML fragments, nothing else. |
| `CALLE_BASE_URL` | no | `https://api.heycall-e.com` | API base. Test env: `https://test-api.heycall-e.com`. |
| `DATABASE_URL` | yes | — | asyncpg Postgres DSN. |
| `CALLE_CONCURRENCY` | no | `2` | Max simultaneous calls per run. Confirm your account concurrency cap before raising. |
| `MAX_TARGETS` | no | `8` | Server-side cap on targets per run (each target is a paid call). |
| `RATE_LIMIT_RUNS` | no | `6` | `POST /runs` per client IP per 10 minutes. |
| `CALLE_CALL_TIMEOUT` | no | `600` | Seconds to wait for one call to reach a terminal state. |

## Usage

- **Registry** (`/banks`) — add, edit, deactivate banks inline. Phones are
  validated E.164 and unique.
- **New request** (`/request`) — group, rhesus, units, bank checklist
  (select-all on), optional ad hoc number with label and an optional
  save-to-registry flag.
- **Run page** (`/runs/{id}`) — live cards plus the ranked shortlist, labeled
  *information only — for a qualified human to act on*.

## Reliability design

- **Queued-first inserts.** Every target row exists before dialing; a crash
  leaves a visible stuck/failed row, never a silent gap. `_recover.py`
  re-drives a row stuck in `dialing` by replaying its persisted idempotency
  key — the API deduplicates, so exactly one call task ever exists.
- **Idempotency keys are persisted before the request** (`run:{id}:bank:{key}:v1`)
  and sent as an `Idempotency-Key` header; network retries are safe.
- **Create and wait are split.** The call id is persisted the moment it
  exists; polling tolerates transient connection errors.
- **Bounded fan out.** A semaphore caps concurrent calls; a server-side cap
  bounds cost per run; a rate limit bounds run creation.
- **Raw evidence retained.** `structured_raw` (unmodified CALL-E response) and
  the transcript are stored beside every parsed column, so a wrong extraction
  can always be audited.

## Swapping in real blood banks

Point targets at real numbers by deactivating the demo banks and adding real
ones in the registry — nothing else changes. Before you do:

1. Obtain consent from each facility to be called by an automated agent, and
   say who is calling on the call itself.
2. Confirm your CALL-E account's concurrency cap and set `CALLE_CONCURRENCY`
   under it.
3. Keep `MAX_TARGETS` and `RATE_LIMIT_RUNS` in place — a bug that dials real
   clinical lines in a loop is the worst failure mode this project has.
4. The agent must still only gather and report; releasing units is the
   facility's and clinician's decision.

## Safety notes

Following the [awesome-phone-call-agents safety
reference](https://github.com/CALLE-AI/awesome-phone-call-agents/blob/main/skills/call-reminder/references/safety.md)
and [design
principles](https://github.com/CALLE-AI/awesome-phone-call-agents/blob/main/docs/design-principles.md):

- **Explicit intent** — calls are placed only when the operator files a
  request naming the targets.
- **E.164 only** — validated on write, unique in the registry; samples use
  reserved fictional numbers (`+1555010...`).
- **No credential exposure** — keys live in `.env`, read server side only;
  there is no client bundle.
- **No hidden or duplicate work** — one run is one visible page of cards;
  idempotency keys prevent duplicate calls across retries.
- **Medical boundary** — this is a logistics tool for stock questions. It
  gives no diagnosis, dosage, treatment, or emergency guidance. For
  emergencies, contact local emergency services.

## Project structure

```text
app/
  main.py        # FastAPI routes: registry CRUD, POST /runs, cards fragment
  dispatch.py    # CallTarget fan-out, semaphore, result persistence
  prompt.py      # CALL-E task prompt + extraction schema
  db.py          # asyncpg pool (small, warm; jsonb codecs)
  templates/     # Jinja2 + htmx (vendored in static/)
migrations/      # plain SQL, reviewer-readable
seed.py          # four fictional demo banks
migrate.py       # applies migrations without psql
_recover.py      # re-drive a row stuck in 'dialing' via idempotent replay
calle_run.py     # the original one-call spike
CALLE_BUILD.md   # the build guidance this repo was built from
```

## License

MIT. See [LICENSE](LICENSE).
