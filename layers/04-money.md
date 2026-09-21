# Layer 4: Money

**Gives the agent:** a way to pay, get paid and hold value.
**Human needed:** funding once, and one identity check for a card. **Cost:** none to set up.
**Identity keys:** `wallet.mailgent_base_usdc`, `wallet.evm.address`, `accounts.stripe`, `card.status`

Ordered by how little the human has to do.

## Pay per request with x402: nothing to sign up for

The Mailgent sign-up in Layer 1 already created a USDC wallet on Base. Services that speak the x402 protocol answer `402 Payment Required` with a price; the agent pays from the wallet and retries. There is no account, no card and no invoice.

```bash
mailgent pay <x402-protected URL>
mailgent activity              # payments sent and received
mailgent mandate create        # optional: a spend limit per call and per day
```

Check whether a paid service accepts x402 before signing up for anything that charges. The human funds the wallet address once with USDC on Base, and only when something paid is needed. The base setup costs nothing.

## Get paid: Stripe

Sign up at dashboard.stripe.com/register with the agent's email. Test mode works immediately; store the secret key under `accounts.stripe`. Live payouts need identity and bank details for a person or a Layer 21 entity, which is a human step: prepare everything and hand over the exact page.

## Pay anywhere a card is required

Card networks require a verified person or company behind every card, so the agent cannot get one alone. The options, least human effort first:

- **AgentCard** (`npm i -g agentcard`, package 0.3.0): the vendor's site describes `agentcard signup --email <agent email>`, then the human runs `agentcard setup` once for an identity check and a payment method, after which the agent issues single-use cards. The flow comes from their website; the npm package has no README to confirm it.
- **Stripe Issuing**, once the Stripe account is live.
- **AgentWallet** (agentwallet.ai): the site describes a KYC step and an API that returns a virtual card, but its API host did not resolve in DNS when checked on 2026-09-21. Do not rely on it until its docs give a working endpoint.

Store only the card token, never the card number. Log every spend with `python3 humanize.py log "<what>" --cost '<amount>'`. Until a card exists, pay with x402 and report the rest as pending.

## Other wallets

Only create these when a task needs another chain. Use any standard keypair library, keep the private key in the Mailgent vault (Layer 13), and put only the address in the identity file under `wallet.evm.address`.

> Status (2026-09-21): `mailgent pay`, `activity` and `mandate` are in the CLI's own README. The card providers are unverified as described above.
