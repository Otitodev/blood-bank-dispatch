# Submission plan — awesome-phone-call-agents

Target repo: <https://github.com/CALLE-AI/awesome-phone-call-agents>
Contribution area: **runnable app** → `apps/python/blood-bank-dispatch/`

## What to copy where

When opening the PR, copy from this repo into the fork:

| This repo | Contributes as |
|---|---|
| `app/` | `apps/python/blood-bank-dispatch/app/` |
| `migrations/`, `migrate.py` | `apps/python/blood-bank-dispatch/` |
| `seed.py` | same (fictional `+1555010...` numbers only) |
| `scripts/run_status.py`, `_recover.py` | `apps/python/blood-bank-dispatch/scripts/` (rename `_recover.py` → `recover_stuck_call.py`) |
| `serve.cmd` + `scripts/*server*.ps1` | replace with a plain `uvicorn` command in the README (Windows-specific files stay out) |
| `README.md` | `apps/python/blood-bank-dispatch/README.md`, trimmed of hackathon specifics |
| `.env.example` | same |
| `CALLE_BUILD.md`, `VIDEO_SCRIPT.md`, `venv/`, `.env` | **not copied** |

## Awesome-list entry (for the target repo README)

```markdown
- [`apps/python/blood-bank-dispatch`](apps/python/blood-bank-dispatch/) - Parallel blood-stock enquiry that dials every blood bank at once on CALL-E, extracts a strict availability schema (with `unknown` preserved as an answer), and returns a shortlist for a human to act on.
```

## Checklist mapped to CONTRIBUTING.md

- [x] English-only content
- [x] No secrets / private numbers (`.env` ignored; samples use `+1555010xxxx`)
- [x] States host + provider (FastAPI app; CALL-E outbound; VAPI mock lines for demo)
- [x] Side effects documented (one paid outbound call per target when `DRY_RUN=0`)
- [x] Setup instructions (README Quick start)
- [x] **No-call path by default** (`DRY_RUN=1` default, principle 7)
- [x] No hidden recurring schedules (there are none; every run is a visible page)
- [x] Duplicate protection (persisted idempotency keys + `Idempotency-Key` header)
- [x] Cancellation/rollback: no recurring jobs to cancel; a run is bounded by `MAX_TARGETS`, per-call timeout, and the queued-first row model (`scripts/recover_stuck_call.py` re-drives stuck rows)
- [x] Manual verification path (`seed.py` → `DRY_RUN` run → `scripts/run_status.py`)
- [ ] `python3 scripts/validate_repository.py` in the fork before opening the PR
- [ ] Branch name: `feat/apps-python-blood-bank-dispatch`

## PR title

```text
feat(apps): add blood-bank-dispatch, a parallel blood-stock enquiry app
```

## Open items before opening the PR

1. Buy/bind four VAPI numbers for the mock lines, dial-test each line by hand
   (§8 rule: call in from a real phone before CALL-E is in the loop).
2. Record the demo video (see `VIDEO_SCRIPT.md`), host it publicly.
3. Cut the README's hackathon-specific framing; keep the safety boundary.
4. Run the repo validation script; open the PR against the correct area
   (`apps/python/`), linking the video and dry-run instructions.
