# Video script — Blood Bank Dispatch (3:00)

Follows CALLE_BUILD.md §12. One continuous screen recording of a single real
run — no stitched takes. Rehearse the blocking against `DRY_RUN=1` first, then
record the live fan-out against the VAPI mock lines in one take.

## Shot list

| Time | On screen | Narration |
|---|---|---|
| 0:00–0:15 | (Optionally a still of a blood bag / clinic corridor) | "A clinic needs three units of O negative. Right now, a lab scientist phones blood banks one at a time — five minutes of hold, transfer, and asking the same seven questions, eight times over." |
| 0:15–0:30 | App on screen, registry page | "This is a dispatch agent built on CALL-E. It dials every blood bank in parallel, asks a fixed set of questions, and returns a ranked shortlist. It only gathers and reports — a human decides." |
| 0:30–0:40 | Request page: pick O negative, 3 units, tick three banks, type a fourth number | "File one request. Three registry banks, one ad hoc number — all dialled at once." |
| 0:40–2:00 | Run page. Four cards appear instantly as queued, flip to dialing, then fill in one by one. **Let it play.** Light zoom-in mid-way. | Minimal narration: "All four dialling in parallel… Bank B has none but offers O positive… Bank C isn't sure what's on the shelf… Bank D wants to call back…" Then: "Every answer comes back as structured data, with the raw transcript stored beside it." |
| 2:00–2:30 | Shortlist below the cards | "Ranked by units available, then time to bedside. This is a shortlist for a qualified human — the agent never reserves, never dispatches, and never makes a clinical decision." |
| 2:30–2:45 | (Still of the shortlist) | "Demo targets are mock lines with a scripted spread of messy answers — stock, alternatives, uncertainty, and a callback request — because real blood-bank calls are never a happy path." |
| 2:45–3:00 | Repo / list page | "It's open source, runs in dry-run mode by default, and lives in the awesome-phone-call-agents repo. Blood Bank Dispatch — compress a twenty-minute calling loop into ninety seconds." |

## Recording rules

1. **Record the run once, for real.** The uninterrupted parallel fill is the
   whole argument; do not edit four takes together.
2. Seed the registry and rehearse filing the exact request beforehand so the
   0:30–0:40 shot takes one attempt.
3. Keep the 0:40–2:00 section honest: if a call drags, cut the *narration*
   short, not the footage.
4. Close with the repo URL on screen long enough to read.
5. Disclosures are non-negotiable: mock lines (2:30) and decision-support-only
   (2:00) must be spoken, not just on screen.
