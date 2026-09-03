import json
import os
import time

from dotenv import load_dotenv
load_dotenv()

from calle import CalleClient, CalleConnectionError, CalleTimeoutError

client = CalleClient(api_key=os.environ["CALLE_API_KEY"])

TASK = "Call +15550101234 and ask whether they can hear clearly."
SCHEMA = {
    "type": "object",
    "required": ["can_hear_clearly"],
    "properties": {
        "can_hear_clearly": {"type": "string", "enum": ["yes", "no", "unknown"]},
    },
}
IDEMPOTENCY_KEY = "spike_hear_clearly_v1"

call = None
for attempt in range(3):
    try:
        call = client.calls.create(
            task=TASK,
            result_schema=SCHEMA,
            metadata={"spike": "hear_clearly_v1"},
            idempotency_key=IDEMPOTENCY_KEY,
        )
        break
    except CalleConnectionError:
        print(f"create attempt {attempt + 1} failed with a connection error, retrying")
        time.sleep(2)
if call is None:
    raise SystemExit("create failed after 3 attempts")

call_id = str(call["id"])
print("call id:", call_id)
print("initial status:", call.get("status"))

deadline = time.monotonic() + 600
while True:
    try:
        call = client.calls.get(call_id)
    except (CalleConnectionError, CalleTimeoutError) as exc:
        print(f"poll error ({type(exc).__name__}), retrying")
        time.sleep(2)
        continue
    if call.get("status") in {"completed", "failed", "canceled"}:
        break
    if time.monotonic() > deadline:
        raise SystemExit("timed out waiting for the call to finish")
    time.sleep(2)

print("top-level keys:", sorted(call.keys()))
for field in ("status", "task_completed", "completion_confidence", "structured_result"):
    print(f"{field}: {call.get(field)!r}")
print("evidence:", json.dumps(call.get("evidence"), indent=2, default=str))
print("recipients:", json.dumps(call.get("recipients"), indent=2, default=str))
