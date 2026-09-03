# BUILD.md — Blood Bank Dispatch Agent (CALL-E hackathon)

Guidance file for coding agents. Read this fully before writing code. Where this
file and the live CALL-E docs disagree, the live docs win: the SDK went from
0.1.0 to 0.7.0 in about ten weeks and has already made breaking changes.

---

## 1. What we are building

A phone agent that finds blood stock fast.

A clinic needs 3 units of O negative. Instead of a lab scientist ringing eight
blood banks one at a time, the operator files one request and the agent dials
every bank in parallel, asks a fixed set of questions, and returns a ranked
shortlist of who has the units and how fast they can reach the patient.

The agent gathers and reports. It never makes a clinical decision, never
reserves, never dispatches. A human reads the shortlist and acts.

### Why this needs phone calls

Blood stock changes hourly, no bank in this market exposes an API, and
asynchronous channels are unreliable for urgent requests. Practitioners already
make these calls by hand. We are compressing a serial 20 minute process into a
parallel 90 second one.

### Judging criteria we are aiming at

| Criterion | How we hit it |
|---|---|
| Real world impact | Specific clinical workflow, described by someone who has done it manually |
| Quality of idea | Parallel fan out does something a human physically cannot do |
| Technical implementation | CALL-E called at runtime, real structured extraction, real persistence |
| Product experience & demo | Live filling result cards, clean three minute video |

---

## 2. Reference docs

Read these before implementing. Do not rely on memory of the CALL-E API.

**CALL-E**
- Developer docs: https://docs.heycall-e.com/
- SDK guide: https://docs.heycall-e.com/#/sdks
- API reference: https://docs.heycall-e.com/#/api-reference
- Webhooks: https://docs.heycall-e.com/#/webhooks
- Changelog: https://docs.heycall-e.com/#/changelog — **check this first, the API is moving**
- Python SDK on PyPI: https://pypi.org/project/calle-ai/
- Python SDK source: https://github.com/CALLE-AI/server-sdk-python
- Integrations repo (install, MCP, CLI, plugins): https://github.com/CALLE-AI/call-e-integrations
- Installation guide: https://raw.githubusercontent.com/CALLE-AI/call-e-integrations/main/docs/install/CALL-E-installation-guide.md

**Submission target**
- Contribution repo: https://github.com/CALLE-AI/awesome-phone-call-agents
- Read its `README.md` and `CONTRIBUTING.md` before creating any folders
- Read its `docs/safety.md` (consent, E.164 handling, credential boundaries,
  medical reminder boundaries) — our domain is medical, so this is directly
  relevant and worth citing in our own README
- Read its `docs/design-principles.md`
- Start from the existing `call-reminder` and `google-form-callback` skills for
  folder shape and README conventions. Match their structure exactly.

**Hackathon**
- https://call-e.devpost.com/ — deadline Sep 14 2026, 11:45pm SGT (4:45pm WAT)

---

## 3. SDK surface as documented (calle-ai 0.7.0)

Install: `pip install calle-ai`. The distribution is `calle-ai`, the import is
`calle`.

```python
import os
from calle import CalleClient

client = CalleClient(
    api_key=os.environ["CALLE_API_KEY"],
    base_url="https://api.heycall-e.com",
)

call = client.calls.create_and_wait(
    task="Call each recipient and ask whether they can attend Friday lunch.",
    recipients=[{"phones": ["+14155550100"], "region": "US", "locale": "en-US"}],
    result_schema={...},            # aggregate across the whole call
    recipient_result_schema={...},  # per recipient extraction
    metadata={"workflow_run_id": "wf_123"},
    idempotency_key="wf_123_friday_lunch",
)

print(call["status"], call["structured_result"])
print(call["task_completed"], call["completion_confidence"], call["evidence"])
print(call["recipients"][0]["structured_result"])
```

Returns are dict-like, not attribute objects. Index with `call["status"]`.

Environment variables:
```
CALLE_API_KEY=...
CALLE_BASE_URL=https://api.heycall-e.com     # test env: https://test-api.heycall-e.com
DATABASE_URL=postgresql://user:pass@host:5432/bb_dispatch
DRY_RUN=1    # no-call by default (contribution repo principle 7); set 0 for live calls
```

### Spike findings — confirmed from installed 0.7.0 source and changelog

1. **Async support: blocking only, confirmed.** The client is a sync `httpx.Client`
   with `time.sleep` polling (`calle/calls.py`). Wrap calls with
   `asyncio.to_thread`; there is no async client.
2. **`create_and_wait` params, confirmed.** Accepts `task`, `recipient` xor
   `recipients`, `result_schema`, `recipient_result_schema`, `metadata`,
   `webhook_url`, `idempotency_key` (sent as an `Idempotency-Key` header), plus
   `interval_seconds` (default 2.0) and `timeout_seconds` (default 600.0).
   Returns a plain dict.
3. **Recipient shape, confirmed.** `{"phones": ["+E164", ...], "locale": "en-US",
   "region": "US"}` — `phones` is a list per recipient.
4. **Webhooks unsigned, confirmed.** Changelog 2026-07-29: deliveries carry
   `CALL-E-Event-Id` only, no secret, timestamp, or signature. Deduplicate on the
   event id and validate the payload shape. `client.webhooks.verify` and
   `client.webhooks.unwrap` exist but are deprecated; do not use them.
5. **Goals API, confirmed present.** `client.goals.run_and_wait(...)` plus
   `list`, `get`, `run`, `get_run`, `wait_for_result`. Note API 0.6 changed Goal
   Run requests to top-level `phone` + `variables`; the `target` wrapper is gone.
6. **Schema features, confirmed.** Supported: `type`, `properties`, `required`,
   `enum`, nested objects, simple `array.items`, `description`,
   `additionalProperties: false`. Unsupported: `$ref`, `oneOf`/`anyOf`/`allOf`,
   recursive schemas, `additionalProperties: true`. Descriptions are passed to
   the extraction model, so write them carefully — they steer extraction.
   The platform itself recommends string enums over booleans and an `unknown`
   member, exactly as section 6 says.
7. **Reserved field names.** `recipient_result_schema` must not use `summary`,
   `status`, `transcript`, `call_id`, or call-timing fields as custom result
   field names. Our schema fields are safe, but keep this list in mind when
   renaming anything.

### Runtime spike results (2026-09-03, live call to a phone we own)

1. **Idempotency replay, confirmed.** The first attempt crashed after create;
   re-POSTing with the same `Idempotency-Key` returned the existing call task
   (`status: completed`) instead of dialling again. The safe-retry design in
   section 6 works exactly as assumed.
2. **Response shape, confirmed, with corrections:**
   - `completion_confidence` is an object `{"score": 0.9, "label": "high"}`,
     not a scalar.
   - Transcripts live at `recipients[n].attempts[m].transcript_turns`, each
     turn `{offset_seconds, speaker, text}`. Serialise this into
     `raw_transcript`.
   - `recipients[n].structured_result` stayed `null` when only `result_schema`
     was sent. Under Option A the aggregate `structured_result` is what we
     read. If we ever send multiple recipients, `recipient_result_schema` is
     mandatory to get per-recipient extraction.
   - Terminal statuses include `completed`, `failed`, `canceled`.
3. **Task prompt looping is real.** On a trivial one-question task the agent
   re-asked "can you hear me clearly" nine times over sixty seconds even after
   three clear confirmations. Every task prompt must include: ask each question
   once, paraphrase at most once if unclear, confirm, end the call. This
   applies to the blood bank script in section 6 and the VAPI lines in
   section 8.

Still open: account concurrency limit (ask support or check the dashboard), and
whether a multi-recipient `recipients` list fans out in parallel.

---

## 4. Data model (Postgres)

Three tables. Use asyncpg or SQLAlchemy, agent's choice, but keep migrations in
plain SQL files so a reviewer can read the schema in one place.

```sql
create table banks (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  phone         text not null unique,   -- E.164, validated on write
  area          text,
  notes         text,                   -- e.g. "ask for the lab, not reception"
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);

create table call_runs (
  id            uuid primary key default gen_random_uuid(),
  blood_group   text not null check (blood_group in ('A', 'B', 'AB', 'O')),
  rhesus        text not null check (rhesus in ('positive', 'negative')),
  units_needed  integer not null,
  requester     text,                   -- facility or person filing the request
  patient_ref   text,                   -- opaque internal ref only, never a name
  status        text not null default 'running',
  created_at    timestamptz not null default now(),
  completed_at  timestamptz
);

create table call_results (
  id                  uuid primary key default gen_random_uuid(),
  run_id              uuid not null references call_runs(id) on delete cascade,
  bank_id             uuid references banks(id),   -- null for ad hoc numbers
  source              text not null,               -- 'registry' | 'adhoc'
  bank_name           text not null,
  phone               text not null,
  status              text not null default 'queued',
  -- queued | dialing | completed | no_answer | callback_requested | failed
  error               text,              -- failure reason when status = 'failed'
  calle_call_id       text,
  idempotency_key     text unique,       -- persisted before the call is placed
  units_available     integer,
  group_confirmed     text,
  screening_status    text,
  release_policy      text,              -- 'will_release' | 'collect_only' | 'refused'
  transport_minutes   integer,
  cost_per_unit       numeric,
  contact_person      text,
  callback_requested  boolean default false,
  alternatives        jsonb,             -- other groups or branches offered
  confidence          numeric,
  raw_transcript      text,
  structured_raw      jsonb,             -- whatever CALL-E returned, unmodified
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- The polled endpoint filters on run_id; FKs are not auto-indexed in Postgres.
create index call_results_run_id_idx on call_results(run_id);

create or replace function touch_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger call_results_touch_updated_at
  before update on call_results
  for each row execute function touch_updated_at();
```

**Non negotiable behaviour:** insert every `call_results` row with status
`queued` *before* any call is placed. The UI polls this table. This gives live
filling cards for free, leaves a visible `failed` row when something crashes
instead of a silent gap, and makes any run replayable if a recording take goes
badly.

Always store `structured_raw` alongside the parsed columns. When extraction is
wrong we need to see what actually came back.

---

## 5. Architecture

```
browser (htmx)  ──POST /runs──▶  FastAPI  ──▶  seed call_results (queued)
     │                            │
     │                            └──▶  fan out ──▶ CALL-E ──▶ mock bank lines
     │                                                 │
     └──GET /runs/{id}/cards, every 2s ◀── Postgres ◀── per call update
```

Single process, single language: FastAPI serves the Jinja templates and the htmx
fragments. Deliberately no Node toolchain — the UI is unstyled content, and one
process is one thing to keep alive while recording. This replaces the original
Next.js plan; do not re-introduce a frontend framework.

### Fan out decision

Two viable shapes. Pick one after the day one spike and write down why.

**Option A — one CALL-E call per bank, N in parallel (default choice).**
`asyncio.gather` over a per bank coroutine, bounded by a semaphore set to the
account concurrency limit. Each bank gets its own `calle_call_id` and its own
row, which is exactly what the live card UI needs and what makes registry and ad
hoc rows interchangeable. More code, better demo, better failure isolation.

**Option B — one CALL-E call with a `recipients` list.**
Fewer moving parts, uses the platform's own fan out, and reads as thorough use
of the API. But per bank status may only resolve when the whole call object
settles, which flattens the live filling effect.

Go with A unless the spike shows a hard concurrency cap, in which case A degrades
gracefully anyway by just running the semaphore at 1 or 2.

### The unified call function

The single most important design rule in this project:

```python
async def call_bank(run: CallRun, target: CallTarget) -> None: ...
```

`CallTarget` is `(name, phone, source, bank_id | None, notes | None)`. A registry
bank and a typed number produce identical `CallTarget` objects. The call
function, the task prompt, the extraction schema, and the results view must not
know or care where a target came from. Keep this boundary clean and mixed runs
are free.

### Mixed runs

The request form submits `{blood_group, rhesus, units_needed, bank_ids: [...],
adhoc_numbers: [...]}`. The backend maps both into one `list[CallTarget]` and
fans out over the whole list in a single gather. Do not run registry and ad hoc
in separate batches; the parallel fan out is the point of the demo.

Ad hoc numbers: validate to E.164, reject anything malformed with a clear error,
and default `bank_name` to the number itself if the user did not type a label.
Support an optional `save_to_registry` flag that inserts into `banks` after a
successful call.

---

## 6. The call task and extraction schema

Write the schema before the call logic. Everything downstream depends on it.

The task prompt should tell CALL-E it is calling on behalf of a named facility,
what is needed, and to ask a specific ordered set of questions. Keep it goal
shaped rather than a rigid script, since goal driven adaptation is what CALL-E is
for. Interpolate the run details rather than hardcoding.

Questions the agent must get through:
1. Units of the requested group and rhesus currently available
2. Screening and cross match status of those units
3. Whether they will release to our facility, or collection only
4. Cost per unit
5. Estimated time to delivery or collection
6. Who to ask for on arrival
7. If they have none: any alternatives, other groups, or a sister branch

`recipient_result_schema` mirrors the `call_results` columns. Set
`additionalProperties: false`, mark everything optional except `units_available`
and `release_policy`, and use enums for `release_policy` and `screening_status`
so we get clean values instead of prose. Include an `unknown` enum member
everywhere, because a hedged answer is real information and must not be coerced
into a false number.

Handle the callback case explicitly: when the bank says someone will ring back,
set `callback_requested`, set status `callback_requested`, and surface it in the
UI as a distinct card state. Do not treat it as a failure and do not try to
receive the callback. Build this last.

Set `idempotency_key` to something durable and derived, such as
`run:{run_id}:bank:{target_key}:v1`, and persist it before the first request so
network retries do not place duplicate calls.

---

## 7. Frontend

Two pages, styled minimal and monochrome — Vercel-like: system fonts, hairline
borders, one accent, status shown as pills with coloured dots. Content still
carries this; CSS must never become the demo.

**Registry page.** Table of banks with inline add, edit, deactivate. Fields:
name, phone, area, notes, active.

**Request page.** Blood group and rhesus selectors, units needed, requester, a
checklist of active banks with select all defaulted on, and a free text field for
an ad hoc number with an optional label and a save to registry checkbox. One
submit button.

**Results view.** One card per target, rendered immediately in `queued` state so
the operator sees all four cards before any call connects. Cards transition
through dialing to a terminal state. Below the cards, a shortlist ranked by units
available then time to bedside, with a clear label that this is information for a
human to act on.

Polling: the results page is a thin shell; the cards and shortlist live in a
fragment at `GET /runs/{id}/cards` that htmx refetches every two seconds
(`hx-trigger="every 2s"`). Do not build websockets for this.

---

## 8. Demo environment

`DRY_RUN=1` simulates all four mock-line personas through the real pipeline —
no calls, no spend. Use it to rehearse the UI and video blocking before
recording against the live VAPI lines.

Live calls to real blood banks are out of scope: we cannot obtain consent from
real facilities to be test targets, and placing unsolicited automated calls to
clinical services would be wrong. Demo against mock lines and disclose this
plainly in the README and video. Judges expect this.

Four VAPI inbound agents, each with a different script:

| Line | Behaviour |
|---|---|
| Bank A | Has 3 units O negative, confirms cross match, quotes price, collection only |
| Bank B | No O negative, offers O positive, offers to check a sister branch |
| Bank C | Puts caller on hold, returns with a partial answer |
| Bank D | The person who knows is unavailable, asks for a callback in 20 minutes |

That spread proves the schema survives messy real conversations rather than one
happy path.

Two traps with agent to agent calls:
- Make the VAPI side terse and reactive. Give it a fixed inventory table and
  instructions to answer only what is asked, never to ask open questions back.
  Two agents both trying to lead will deadlock or talk over each other.
- Increase endpointing delay on the VAPI side so it stops interrupting CALL-E
  mid sentence. This is the single thing that makes these recordings sound broken.

Test each VAPI line by dialing in from a real phone before putting CALL-E in the
loop.

Budget: with a four way fan out, every full run costs four calls. Debugging will
eat the allowance fast. Test single target runs against one mock line while
building, and save full fan outs for integration checks and recording.

---

## 9. Safety and data handling

Read `docs/safety.md` in the contribution repo and follow it. Our own rules:

- Never store a patient name. `patient_ref` is an opaque internal string only.
- Never let the agent commit, reserve, or promise anything. It asks and reports.
- The README must state prominently that output is decision support for a
  qualified human, not a clinical recommendation.
- All phone numbers stored and transmitted in E.164.
- API keys server side only. The browser gets htmx and HTML fragments and
  nothing else; there is no client bundle.
- The demo uses mock recipients. Say so in the README, the video, and the PR.
- Rate limit the request endpoint. A bug that dials a real number in a loop is
  the worst failure mode this project has.
- Cap targets per run server side (eight is a sensible ceiling), not just in
  the UI. Every target in the fan out is a paid call.

---

## 10. Build order

Do not reorder. Each step gates the next.

1. **Spike.** Install the SDK, place one call to a phone you own, confirm the
   response shape and the concurrency limit. Nothing else until this passes.
2. **Repo shape.** Read the contribution repo README and CONTRIBUTING, mirror the
   folder structure of an existing skill. Getting this wrong is the cheapest way
   to lose points.
3. **Schema.** Extraction schema and Postgres migrations. Both, before any call
   logic.
4. **Mock lines.** Four VAPI agents, verified by dialing in manually.
5. **Single call path.** One request, one target, one persisted result.
6. **Fan out.** `asyncio.gather` with semaphore, mixed registry and ad hoc.
7. **Ranking.** Shortlist by units then time.
8. **Frontend.** Registry page, request page, polling results view.
9. **Callback handling.** The messiest case, and the most skippable if time runs out.
10. **Video and PR.**

---

## 11. Definition of done

- [ ] A mixed run of three registry banks plus one typed number completes end to
      end and persists four rows with distinct structured results
- [ ] Every terminal status is reachable and visibly distinct in the UI
- [ ] `structured_raw` is stored for every completed call
- [ ] Registry survives a restart
- [ ] No API key in any client bundle
- [ ] README documents setup, env vars, the mock line disclosure, the safety
      boundary, and how to swap in real numbers
- [ ] PR opened against the correct contribution area
- [ ] Demo video under three minutes, public, showing a real run
- [ ] Devpost form has the PR URL, the video, and the CALL-E account email
- [ ] Feedback survey submitted

---

## 12. Video script skeleton (three minutes)

- 0:00 The problem, told first hand. A clinic needs O negative, someone starts
  dialing banks one by one, each call is five minutes of hold and transfer.
- 0:15 What the skill does, in one sentence.
- 0:30 File a request, tick three banks, type a fourth number.
- 0:40 Four cards appear as queued, then fill in live. Let this play.
- 2:00 The structured output, and that it is a shortlist for a human.
- 2:30 Limitations: mock lines, no reservation, decision support only.
- 2:45 Where to find the skill.

Record the run once for real rather than editing four takes together. The
uninterrupted parallel fill is the whole argument.
