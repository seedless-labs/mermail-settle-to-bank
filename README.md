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
```

## Provider interface

Four calls: `beneficiaries.list`, `quote`, `send`, `status`. Any provider that takes a stablecoin payment and pays a local bank account fits. The reference rail is [Seedless](https://seedlesslabs.xyz), where USDC reaches a Nigerian bank account in under a minute.

## Status

Companion skill, per Mermail's [contribution guide](https://github.com/Nudgen-Marketing/mermail-skills/blob/main/CONTRIBUTING.md): it combines Mermail with an outside settlement rail and owns none of Mermail's tools. An official proposal is open on the skills repo.

MIT licensed.
