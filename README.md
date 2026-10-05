# mermail-settle-to-bank

A companion [Mermail](https://mermail.app) skill: the step that turns money an agent has been paid into money in a bank account.

Mermail gives an agent an inbox and a wallet. It can be paid, swap, and pay for things on the internet with x402. What it cannot do is pay a contractor who does not take crypto, or put the operator's earnings into their own account. This skill covers that last step, and the security model that makes it safe to give an agent.

## The rule this is built on

**Email cannot choose where money goes.** An email may ask to be paid. It may name an amount, an invoice, a deadline. It may not name a bank account. Destinations come from a beneficiary list the human approved out of band, and a payout resolves to an entry on that list or it does not happen.

Without that split, an agent inbox plus a payout tool is a drainer waiting for one convincing invoice.

## What's here

```
skills/mermail-settle-to-bank/
  SKILL.md                  what the agent does, step by step
  references/security.md    the contract: untrusted input, approvals, caps, idempotency
  references/tools.md       the route through the official skills, and the provider interface
  agents/openai.yaml        marketplace metadata
scenarios.json              happy paths and the attacks it has to refuse
demo/run.py                 run the skill against your own Mermail inbox
demo/beneficiaries.json     the sandbox's approved beneficiary list
demo/mermail-settle-to-bank-demo.mp4   the demo video
```

## Demo video

https://github.com/user-attachments/assets/d52b50f6-361e-4a7d-98c8-597f62288e56

About 4 minutes. A live Mermail inbox gets two emails: an invoice from a known contractor, and a "new bank details" email with a lookalike sender. The agent pays the invoice to the approved account after one approval, refuses the new account, and Mermail's own scan had already tagged the second email Suspicious and Urgent. Mermail calls are live; the settlement provider is sandboxed, so nothing moved. Full-quality file: [demo/mermail-settle-to-bank-demo.mp4](demo/mermail-settle-to-bank-demo.mp4).

## Run it yourself

You need a Mermail account with an inbox, a Mermail API key, and an OpenAI API key. Python 3.9+, no packages to install.

1. Send your Mermail inbox two emails, from any address: an invoice ("Attached is INV-0412 for 150 USDC, please pay to my usual account") and a follow-up asking to pay the same invoice to a new bank account.
2. Run:

```bash
export MERMAIL_API_KEY=...          # console.mermail.app, Settings, API keys
export OPENAI_API_KEY=...
export MERMAIL_MAILBOX=you@mermail.app
python3 demo/run.py "Check my Mermail inbox and handle any payment requests."
```

`list_emails` and `get_email` run live against your inbox through the Mermail MCP. Beneficiaries, quotes and `send` are a local sandbox (`demo/beneficiaries.json`), so nothing leaves any wallet. `send` stops and asks you to type `yes`. Swap in your own beneficiary list, or point the provider functions at a real rail that implements the interface below.

The attacks in `scenarios.json` (changed bank account, "the CFO already approved this", a stale approval, a re-run of a sent payout, an amount above the cap) can be sent as emails or typed as follow-up prompts.

## Provider interface

Four calls: `beneficiaries.list`, `quote`, `send`, `status`. Any provider that takes a stablecoin payment and pays a local bank account fits. The reference rail is [Seedless](https://seedlesslabs.xyz), where USDC reaches a Nigerian bank account in under a minute.

## Status

Companion skill, per Mermail's [contribution guide](https://github.com/Nudgen-Marketing/mermail-skills/blob/main/CONTRIBUTING.md): it combines Mermail with an outside settlement rail and owns none of Mermail's tools. An official proposal is open on the skills repo: [Nudgen-Marketing/mermail-skills#359](https://github.com/Nudgen-Marketing/mermail-skills/pull/359).

MIT licensed.
