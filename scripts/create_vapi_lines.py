"""Create or update the four §8 mock-line assistants on VAPI.

Terse, reactive, fixed-inventory lines per CALLE_BUILD.md §8: answer only what
is asked, never ask open questions back, conservative endpointing so the VAPI
side never interrupts CALL-E mid-sentence.

Idempotent: matches by assistant name and PATCHes when config drifts.
Does NOT purchase or bind phone numbers — see --numbers to inspect binding.
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API = "https://api.vapi.ai"
KEY = (os.environ.get("VAPI_API_KEY") or "").strip().strip('"')


def conservative_voice() -> dict:
    # §8: "Increase endpointing delay on the VAPI side so it stops
    # interrupting CALL-E mid sentence."
    return {
        "startSpeakingPlan": {
            "waitSeconds": 0.8,
            "transcriptionEndpointingPlan": {
                "onPunctuationSeconds": 0.2,
                "onNoPunctuationSeconds": 1.5,
                "onNumberSeconds": 0.8,
            },
        },
        "stopSpeakingPlan": {
            "numWords": 2,
            "voiceSeconds": 0.2,
            "backoffSeconds": 1.0,
        },
    }


COMMON_RULES = """
Hard rules:
- Answer only what is asked. One short sentence per answer, under 25 words.
- Never ask open questions back. A brief clarification is allowed, nothing more.
- Never take orders, never promise to reserve, hold, or set aside units.
- You are speaking to an automated clinic stock-check line. Do not say you are an AI.
- If asked about something you do not know, say you do not know.
"""

ASSISTANTS = [
    {
        "name": "BB Mock Bank A",
        "firstMessage": "Blood bank lab, good afternoon.",
        "system": """You are the lab technician at Blood Bank A. Fixed facts:
- Stock: exactly 3 units of O negative, screened and cross-match ready.
- Price: 2,000 per unit.
- Release: in-person collection only; you do not deliver.
- Contact: ask for June at the lab desk.
""" + COMMON_RULES,
    },
    {
        "name": "BB Mock Bank B",
        "firstMessage": "Blood bank B, hello.",
        "system": """You are the front desk at Blood Bank B. Fixed facts:
- You have NO O negative at all.
- You do have 2 units of O positive.
- There is a sister branch on Abuja road; you do not know their stock.
Only mention the O positive units and the sister branch if the caller asks
about alternatives, other groups, or other branches.
""" + COMMON_RULES,
    },
    {
        "name": "BB Mock Bank C",
        "firstMessage": "Blood bank C, one moment please.",
        "system": """You are a distracted assistant at Blood Bank C. Script:
- When asked how many units of O negative you have, say: "One moment, let me check the fridge." (Then answer, as if you walked away and came back.)
- After checking: you can see around 3 bags labelled O negative, but you are NOT sure of the screening or cross match status, and you do not know price or delivery time.
- Your answers should sound like you half-read a label from across the room.
""" + COMMON_RULES,
    },
    {
        "name": "BB Mock Bank D",
        "firstMessage": "Blood bank D, good afternoon.",
        "system": """You are the receptionist at Blood Bank D. Script:
- Whoever knows the blood stock (the blood bank manager) has stepped out.
- For ANY stock, price, screening, or delivery question: say the manager just stepped out and someone will call them back in about 20 minutes.
- Do not attempt to answer any stock question yourself. Ask for the caller's facility name and number so the manager can return the call.
""" + COMMON_RULES,
    },
]


def assistant_payload(a: dict) -> dict:
    return {
        "name": a["name"],
        "firstMessage": a["firstMessage"],
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "messages": [{"role": "system", "content": a["system"]}],
        },
        "silenceTimeoutSeconds": 30,   # Bank C needs to survive its "hold"
        "maxDurationSeconds": 300,     # hard cost cap per call
        "backgroundSound": "office",
        **conservative_voice(),
    }


def main() -> None:
    show_numbers = "--numbers" in sys.argv
    headers = {"Authorization": f"Bearer {KEY}"}
    with httpx.Client(timeout=30, headers=headers) as client:
        existing = client.get(f"{API}/assistant").json()
        by_name = {a.get("name"): a for a in existing}

        for a in ASSISTANTS:
            payload = assistant_payload(a)
            current = by_name.get(a["name"])
            if current is None:
                r = client.post(f"{API}/assistant", json=payload)
                r.raise_for_status()
                print(f"created  {a['name']}: {r.json()['id']}")
            else:
                drift = any(current.get(k) != v for k, v in payload.items())
                if drift:
                    r = client.patch(f"{API}/assistant/{current['id']}", json=payload)
                    r.raise_for_status()
                    print(f"updated  {a['name']}: {current['id']}")
                else:
                    print(f"in-sync  {a['name']}: {current['id']}")

        if show_numbers:
            numbers = client.get(f"{API}/phone-number").json()
            print(f"\nphone numbers on account: {len(numbers)}")
            for n in numbers:
                num = n.get("number") or "?"
                print(f"  ...{num[-4:]}  assistant={n.get('assistantId') or '(none)'}")
            if not numbers:
                print("  (none — the mock lines need numbers to be dialable)")


if __name__ == "__main__":
    main()
