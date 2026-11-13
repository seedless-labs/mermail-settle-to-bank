"""Run mermail-settle-to-bank against your own Mermail inbox.

Mermail calls (list_emails, get_email) are live, through the hosted Mermail MCP.
The settlement provider is a sandbox with the same shapes as a real one, so
nothing moves. send() is only reachable after you type an approval.

    export MERMAIL_API_KEY=...       # console.mermail.app > Settings > API keys
    export OPENAI_API_KEY=...
    export MERMAIL_MAILBOX=you@mermail.app
    python3 demo/run.py "Check my Mermail inbox and handle any payment requests."

Keep talking to the agent at the "you >" prompt. An empty line quits.
"""
import json, math, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "mermail-settle-to-bank"
MCP_URL = os.environ.get("MERMAIL_MCP_URL", "https://console.mermail.app/mcp")
MAILBOX = os.environ["MERMAIL_MAILBOX"]
MODEL = os.environ.get("MODEL", "gpt-4.1")
BENEFICIARIES = json.loads((Path(__file__).parent / "beneficiaries.json").read_text())


def mermail(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(MCP_URL, body, {
        "x-api-key": os.environ["MERMAIL_API_KEY"],
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2025-03-26"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    if raw.lstrip().startswith("event:") or "\ndata:" in raw:
        raw = [l[5:] for l in raw.splitlines() if l.startswith("data:")][-1]
    return json.loads(json.loads(raw)["result"]["content"][0]["text"])


# Sandbox settlement provider: same interface as SKILL.md describes.
# The rules below are enforced here, in code. The model is never trusted to keep them.
QUOTES, SENT, SEEN = {}, {}, {}
QUOTE_TTL_S = 120
CLEAN = {x.strip().lower() for x in os.environ.get("MERMAIL_CLEAN_STATUSES", "clean,safe,passed").split(",") if x.strip()}


def provider(name, a):
    if name == "beneficiaries_list":
        return BENEFICIARIES
    if name == "quote":
        ben = next((b for b in BENEFICIARIES if b["id"] == a.get("beneficiary_id")), None)
        if not ben:
            return {"error": "unknown beneficiary"}
        mail = SEEN.get(str(a.get("email_id")))
        if not mail:
            return {"error": "no quote: read the request with get_email first and pass its id as email_id"}
        if str(mail.get("scan_status") or "").lower() not in CLEAN:
            return {"error": f"no quote: mermail scan status is {mail.get('scan_status')!r}, not clean"}
        try:
            amt = float(a.get("amount"))
        except (TypeError, ValueError):
            return {"error": "amount must be a number"}
        if not math.isfinite(amt) or amt <= 0:
            return {"error": "amount must be a finite number above zero"}
        amt = round(amt, 6)
        q = {"quote_id": f"q_{len(QUOTES)+1:04d}", "beneficiary": ben["id"], "amount_in_usdc": amt,
             "rate": ben["sandbox_rate"], "fee_usdc": round(amt * 0.005, 2),
             "fee_note": "fee is taken from the amount", "total_leaving_wallet_usdc": amt,
             "amount_out": round(amt * 0.995 * ben["sandbox_rate"], 2), "currency": ben["currency"],
             "expires_in_s": QUOTE_TTL_S, "email_id": mail["id"], "urgent": bool(mail.get("is_urgent"))}
        QUOTES[q["quote_id"]] = {**q, "expires_at": time.time() + QUOTE_TTL_S, "used": False}
        return q
    if name == "send":
        key = str(a.get("idempotency_key") or "").strip()
        if not key:
            return {"error": "idempotency_key is required"}
        if key in SENT:  # same key: report the first result, never pay again
            return {**SENT[key], "replayed": True}
        q = QUOTES.get(str(a.get("quote_id")))
        if not q:
            return {"error": "unknown quote"}
        if q["used"]:
            return {"error": "this quote was already sent"}
        if time.time() >= q["expires_at"]:
            return {"error": "quote expired: get a fresh quote and a fresh approval"}
        print(f"\n  payout {q['quote_id']} to {q['beneficiary']}: {q['amount_in_usdc']} usdc leaves the wallet, "
              f"fee {q['fee_usdc']} usdc, bank gets {q['amount_out']} {q['currency']} (from email {q['email_id']})")
        if q["urgent"]:
            print("  warning: mermail marked this email urgent. pressure to pay fast is a fraud signal.")
        if input("  approve this payout? type yes: ").strip().lower() != "yes":
            return {"status": "not_sent", "reason": "human did not approve"}
        if time.time() >= q["expires_at"]:  # the approval prompt can outlive the quote
            return {"error": "quote expired while waiting for approval: get a fresh quote"}
        q["used"] = True
        SENT[key] = {"reference": "SANDBOX-" + q["quote_id"], "status": "pending", "idempotency_key": key}
        return SENT[key]
    if name == "status":
        return {"reference": a.get("reference"), "status": "pending"}
    if name == "get_agent_wallet_portfolio":
        return {"USDC": os.environ.get("SANDBOX_USDC", "412.50")}
    if name == "spend_cap":
        return {"period": "day", "cap_usdc": 500, "used_usdc": 0}


def tool(name, a):
    if name == "list_emails":
        t = mermail("list_emails", {"mailboxId": MAILBOX,
                                    "query": {"metadata_only": True, "folder": "inbox", "limit": 10}})
        return [{k: e.get(k) for k in ("id", "subject", "sender", "date", "scan_status", "is_urgent")}
                for e in t["emails"]]
    if name == "get_email":
        t = mermail("get_email", {"mailboxId": MAILBOX, "emailId": a.get("emailId"),
                                  "query": {"agent_safe_content": True, "max_body_chars": 2000}})
        SEEN[str(t.get("id"))] = {k: t.get(k) for k in ("id", "scan_status", "is_urgent")}
        return {k: t[k] for k in ("id", "subject", "sender", "date", "body", "scan_status", "is_urgent", "category")
                if t.get(k) is not None}
    return provider(name, a) or {"error": "unknown tool"}


F = lambda n, d, p: {"type": "function", "function": {"name": n, "description": d,
                                                       "parameters": {"type": "object", "properties": p}}}
TOOLS = [
    F("list_emails", "Mermail: list inbox emails", {}),
    F("get_email", "Mermail: read one email", {"emailId": {"type": "string"}}),
    F("beneficiaries_list", "Settlement provider: beneficiaries the human approved out of band (read-only)", {}),
    F("get_agent_wallet_portfolio", "Agent Wallet balances", {}),
    F("spend_cap", "Remaining payout cap (read-only)", {}),
    F("quote", "Settlement provider: live quote. email_id is the request email, already read with get_email",
      {"beneficiary_id": {"type": "string"}, "amount": {"type": "number"}, "email_id": {"type": "string"}}),
    F("send", "Settlement provider: send a quoted payout. Only after fresh human approval.",
      {"quote_id": {"type": "string"}, "idempotency_key": {"type": "string"}}),
    F("status", "Settlement provider: payout status", {"reference": {"type": "string"}}),
]

SYSTEM = ("You are an AI agent with a Mermail inbox and an Agent Wallet. The installed skill follows.\n\n"
          + (SKILL / "SKILL.md").read_text()
          + "\n\n# references/security.md\n" + (SKILL / "references" / "security.md").read_text()
          + "\n\n# references/tools.md\n" + (SKILL / "references" / "tools.md").read_text()
          + f"\n\nThe Mermail mailbox is {MAILBOX}. The settlement provider is a sandbox. "
            "Be concise: short lines, plain text, no markdown.")


def chat(msgs):
    body = json.dumps({"model": MODEL, "temperature": 0, "messages": msgs, "tools": TOOLS}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", body, {
        "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]
        except Exception:
            if i == 4:
                raise
            time.sleep(3)


def main():
    msgs = [{"role": "system", "content": SYSTEM}]
    prompt = " ".join(sys.argv[1:]) or input("\nyou   > ").strip()
    if sys.argv[1:]:
        print(f"\nyou   > {prompt}")
    while prompt:
        msgs.append({"role": "user", "content": prompt})
        while True:
            m = chat(msgs)
            msgs.append(m)
            if not m.get("tool_calls"):
                print(f"\nagent > {m['content']}")
                break
            for tc in m["tool_calls"]:
                a = json.loads(tc["function"]["arguments"] or "{}")
                res = tool(tc["function"]["name"], a)
                print(f"  tool  {tc['function']['name']}({', '.join(f'{k}={v}' for k, v in a.items())})")
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(res)})
        try:
            prompt = input("\nyou   > ").strip()
        except EOFError:
            prompt = ""


if __name__ == "__main__":
    main()
