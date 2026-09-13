# Blood Bank Dispatch

## One-line Summary

Blood Bank Dispatch turns a clinic's serial blood-stock phone chase into one bounded parallel CALL-E run that returns a ranked, auditable shortlist for a qualified human.

## Inspiration

Blood availability is unusually time-sensitive, but the information needed to locate it often lives behind phone calls rather than APIs. When a clinic needs a specific blood group and rhesus factor, a laboratory scientist may have to call several blood banks one after another, wait through holds and transfers, repeat the same questions, and manually compare incomplete answers. Stock can change while that calling loop is still in progress.

That made this a compelling phone-agent problem: not a generic assistant, but a narrow workflow where CALL-E can do something a person physically cannot do alone—contact several authorized facilities in parallel and turn their answers into one comparable result. The goal was to reduce the phone chase while keeping every clinical and operational decision with qualified humans.

## What it does

Blood Bank Dispatch lets an authenticated clinic operator maintain a registry of blood banks and file one request containing the blood group, rhesus factor, units needed, and target facilities. Registry targets and an optional authorized ad hoc number can be included in the same run.

The application creates a visible result card for every target before dialing begins, then fans out CALL-E calls with bounded concurrency. Each voice agent asks the same ordered questions about stock, screening and cross-match status, release policy, cost, transport time, the correct contact person, and possible alternatives. As calls finish, the cards fill with structured results and the application produces a shortlist ranked by units available and then time to bedside.

Uncertain or hedged answers remain `unknown` instead of being forced into a confident value. The raw CALL-E response and transcript are retained beside the parsed fields for auditability. Blood Bank Dispatch only gathers and reports: it never reserves blood, dispatches units, promises availability, or makes a clinical decision.

## How we built it

We built a single Python service with FastAPI, server-rendered Jinja templates, htmx polling, and Postgres. The deliberately small architecture keeps the live workflow easy to run and understand: the browser files a request, one database transaction creates the run and all of its queued target rows, and an asynchronous dispatcher processes those targets behind a configurable semaphore.

For every target, the dispatcher invokes the CALL-E Python SDK at runtime. Because the SDK is synchronous, the application runs its create and wait operations through `asyncio.to_thread` so the FastAPI event loop remains responsive. Each target receives a durable idempotency key that is stored before the external request; a retry can recover the existing CALL-E task instead of placing a duplicate call.

The CALL-E task prompt contains a fixed question order and explicit end conditions. Its strict JSON schema captures availability, release and screening states, transport time, cost, contact details, alternatives, and callback requests. Postgres stores both the normalized fields and the raw evidence. The UI polls a small HTML fragment every two seconds, so queued cards, active calls, completed results, and the ranked shortlist update without a separate frontend framework.

We also built a no-call mode that simulates varied outcomes through the complete persistence and UI pipeline. Live demonstrations use consenting VAPI mock lines representing stock, alternatives, uncertainty, callbacks, and no-answer behavior; no real blood bank is contacted for the demo.

## Challenges we ran into

- **Making parallel calls reliable.** External phone calls are slow and failure-prone. We had to combine bounded concurrency, queued-first database writes, early call-ID persistence, idempotency keys, and a recovery path so a network or process failure would remain visible and would not silently double-dial a facility.
- **Turning messy speech into honest data.** Real callers hedge, pause, go on hold, offer alternatives, or ask to call back. The extraction schema needed explicit `unknown` values and a distinct callback state so ambiguity remained information rather than becoming a fabricated answer or generic failure.
- **Keeping the voice agent focused.** Early CALL-E experiments showed that a loose task could repeat questions. We added an ordered question set, a one-paraphrase limit, clear completion conditions, and instructions never to reserve or promise anything.
- **Building safely in a medical-adjacent domain.** Phone destinations, credentials, and patient context required strong boundaries. The app is password-gated, masks numbers in rendered views, validates E.164 numbers, limits request rates and target counts, uses no patient names, and runs with phone calls disabled by default.
- **Designing an honest demonstration.** Calling real clinical services without consent would be unacceptable. We created controlled mock lines with deliberately imperfect answers so the demo can prove the workflow without pretending the data came from real facilities.

## Accomplishments that we're proud of

- CALL-E is not a label on top of the project; it is imported and called at runtime for every live target, and its structured result drives the product experience.
- Every intended result exists before dialing starts, so the operator never loses sight of a target even when a call or worker fails.
- The same path supports registry and ad hoc targets, safe dry runs, live mock-line calls, structured extraction, persistent raw evidence, and a useful ranked shortlist.
- The project treats safety as product behavior: human decision authority, no reservations, masked destinations, explicit authorization boundaries, cost controls, and mock-line disclosure are present in the code, interface, documentation, and demo plan.
- The runnable app is open source and has a public contribution pull request to CALL-E's `awesome-phone-call-agents` repository.

## What we learned

Phone agents need much tighter completion rules than text assistants. A good prompt must say what to ask, how often to clarify, when to stop, and what the agent is never allowed to promise.

We also learned that uncertainty deserves a first-class representation. An `unknown` enum value, a callback state, and stored raw evidence produce a more trustworthy system than a schema that forces every conversation into a clean answer.

Finally, the hard part of parallel automation is not starting several tasks—it is preserving visibility and control when one of them fails. Transactions, idempotency, bounded concurrency, and safe defaults were as important to the product as the voice interaction itself.

## What's next for bb-dispatch

The next step is a supervised pilot with consenting facilities, using real operational feedback to refine the question order, terminology, and shortlist. We would add automated integration tests, stronger background-job durability, clearer per-call audit views, and monitoring for stuck or unusually long runs.

We also want to support human-confirmed follow-up workflows: a staff member could select an option from the shortlist and initiate the facility's approved reservation or collection process without allowing the agent to make that commitment itself. Callback reconciliation, facility-specific scripts, regional routing, and verified inventory integrations could further reduce manual work while preserving the same human safety boundary.

## How We Used AI

CALL-E is invoked at runtime for each target. Its voice agent conducts the natural-language call, adapts when a person is uncertain or offers an alternative, and extracts the conversation into a strict JSON schema. The schema captures units available, confirmed group, screening and cross-match state, release policy, transport time, cost, contact person, callback requests, and alternatives.

The prompt tells the agent to ask each question once, paraphrase at most once when unclear, and end without making a reservation or commitment. String enums include an `unknown` value so ambiguous speech remains visible instead of becoming a fabricated answer. The full CALL-E response and flattened transcript are retained for auditability.

## How We Used Codex

Codex was used as the coding agent throughout the build: translating the workflow into a FastAPI/Postgres implementation, inspecting the CALL-E Python SDK behavior, shaping the extraction schema and call prompt, and iterating on reliability and safety controls. The commit history records hardening work around queued-first transactional creation, persisted idempotency keys, bounded concurrency, recovery of interrupted calls, operator authentication, login throttling, authorized destinations, input limits, and phone-number masking.

Codex also helped create the safe dry-run simulator, the four mock-line personas, deployment and test instructions, and the demo/submission materials. The current preparation pass reviewed the implementation against the live Devpost form and judging criteria and checked the demo narration against the actual concurrency and simulator behavior.

## Key Features

- Registry of reusable blood-bank targets with E.164 validation and masked display.
- One request combining registry targets with an optional authorized ad hoc number.
- Transactional queued-first creation so every intended call is visible before dialing.
- Bounded asynchronous fan-out with one CALL-E task and durable idempotency key per target.
- Strict structured extraction with explicit uncertainty, alternatives, and callback handling.
- Polling result cards and a shortlist ranked by available units and transport time.
- Stored raw CALL-E response and transcript for later audit.
- Safe-by-default `DRY_RUN=1` mode with no phone calls or CALL-E spend.
- Password-gated operator interface, rate limits, target caps, and masked phone numbers.
- Manual recovery path for a row interrupted while dialing.

## Architecture

```text
Browser + htmx
    -> FastAPI request endpoint
    -> one Postgres transaction creates the run and all queued result rows
    -> asyncio fan-out with a configurable semaphore
    -> CALL-E Python SDK, one call task per target
    -> structured result + transcript + raw response persisted in Postgres
    -> htmx polls the cards fragment every two seconds
    -> completed rows are ranked into a human-action shortlist
```

The application is deliberately a single Python service with server-rendered Jinja templates. There is no client-side application bundle and API credentials remain server-side.

## Testing Instructions

### Safe dry-run path

1. Use Python 3.12 or another compatible Python 3 release.
2. Create a virtual environment and install `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Set `DATABASE_URL` to a Postgres database and set a non-empty `APP_PASSWORD`.
5. Leave `DRY_RUN=1`; this path places no calls and does not require a CALL-E API key.
6. Run `python migrate.py` and `python seed.py`.
7. Start the app with `python -m uvicorn app.main:app --port 8000`.
8. Open `http://localhost:8000`, sign in, and open **New request**.
9. Request three units of O negative blood and select the four fictional demo banks.
10. Dispatch the run and observe every result card appear before work begins, transition through its states, and populate the shortlist.

### Live CALL-E path for authorized mock lines

1. Bind consenting mock phone lines and replace the fictional seed numbers with their E.164 numbers.
2. Set `CALLE_API_KEY`, set `DRY_RUN=0`, and keep `CALLE_CONCURRENCY` within the account limit.
3. For any ad hoc target, include its number in `ALLOWED_DESTINATIONS`.
4. Run a single-target check before a multi-target fan-out.
5. Never aim the demonstration at real clinical services without explicit authorization.

## Public Demo Link

Optional functional deployment: **TODO — add a public URL if one will be kept available for judging.**

Local setup and safe dry-run instructions are provided above.

## Public Repository Link

Project repository: https://github.com/Otitodev/blood-bank-dispatch

Required CALL-E contribution pull request: https://github.com/CALLE-AI/awesome-phone-call-agents/pull/298

## Demo Video

Public YouTube or Vimeo URL: **TODO — record, upload publicly, and paste the URL.**

Target duration: 2 minutes 50 seconds, leaving a ten-second safety margin below the official three-minute limit. The working narration and shot plan are in `VIDEO_SCRIPT.md`.

The recording should show:

1. The manual phone-work problem and human decision boundary.
2. The masked registry and one O-negative request.
3. All result rows appearing before dialing and the bounded CALL-E fan-out progressing.
4. At least two meaningfully different outcomes, such as stock, an alternative, uncertainty, callback requested, or no answer.
5. The ranked shortlist and its decision-support label.
6. The public contribution repository or pull request.
7. Spoken disclosure that all targets are mock lines and no clinical decisions or reservations are made.

## Screenshot Shot List

1. Authenticated bank registry with masked phone numbers.
2. New request form configured for three units of O negative across several targets.
3. Run page while cards are queued or dialing.
4. Completed cards showing divergent structured outcomes.
5. Ranked shortlist with the human-action safety notice.

## Submission Readiness Notes

Verified during this preparation pass:

- The repository was created during the hackathon submission period; its first commit is dated September 3, 2026.
- Python bytecode compilation succeeds for the application and utility scripts.
- The installed Python environment reports no broken package requirements.
- `.env` and local planning documents are ignored; `.env.example` is the tracked configuration template.
- The implementation contains real CALL-E SDK calls, structured extraction, persisted call IDs, idempotency keys, transcripts, and raw results.
- The required contribution is open as [CALLE-AI/awesome-phone-call-agents#298](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/298) with the expected Blood Bank Dispatch title and branch.

Remaining required work:

- Record and publicly upload the under-three-minute demo video.
- Confirm the official form attestations and participant fields below.
- Perform one final live mock-line rehearsal at the exact recording concurrency.
- Correct two over-broad PR-description claims: the current implementation uses aggregate `result_schema`, not `recipient_result_schema`, and uses polling without implementing a webhook handler.

Review caveats:

- There is no automated test suite; this pass verified compilation and dependency consistency, not a full Postgres/CALL-E integration run.
- In the outer dispatch exception path, an SDK exception is stored and rendered without explicitly replacing the target number. If an upstream error message contains that number, it could bypass the otherwise consistent masking policy. Fix or verify this before recording a forced-failure case.
- The default `CALLE_CONCURRENCY` is 2. Do not narrate four simultaneous calls unless the recording environment is intentionally set to 4 and the CALL-E account supports it.

## Known Limitations

- Availability still depends on what a person says during a phone call; the shortlist can be stale or incorrect and must be verified by qualified staff.
- The system does not reserve, order, dispatch, diagnose, recommend treatment, or receive callbacks.
- Live operation requires CALL-E access, Postgres, authorized destinations, and consent from called facilities.
- Background dispatch runs in the web process. A process restart can require the provided manual idempotent recovery path.
- The interface polls every two seconds rather than using push updates.
- No public functional deployment URL is currently recorded in this draft.

## TODO Official Form Fields

- **Submitter Type:** TODO — choose `Individual`, `Team`, or `Organization`.
- **Country of residence/incorporation:** TODO — enter every required country accurately.
- **Organization name:** Optional; add only if applicable.
- **App status:** `Newly created`.
- **If pre-existing, explain updates:** `Not applicable — Blood Bank Dispatch was newly created during the submission period.`
- **Testing instructions for application:** Use the **Testing Instructions** section above.
- **Optional functional demo URL:** TODO or leave blank.
- **Project submission pull request URL:** `https://github.com/CALLE-AI/awesome-phone-call-agents/pull/298`.
- **Email associated with CALL-E account:** `otitodrichukwu@gmail.com`.
- **Primary use case:** `Service coordination & dispatch`.
- **One-sentence task:** `Blood Bank Dispatch calls multiple authorized blood-bank lines, extracts comparable stock and logistics answers, and ranks the available options for qualified clinic staff.`
- **Eligible Age:** TODO — participant must personally confirm.
- **Country eligibility:** TODO — participant must personally confirm.
- **Conflict of interest:** TODO — participant must personally confirm.
