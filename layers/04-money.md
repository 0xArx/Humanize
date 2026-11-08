# Layer 4: Money

**Gives the agent:** a way to pay, get paid and hold value, without a payment vendor sitting between the agent and its funds.
**Human needed:** funding once, and one identity check for a card. **Cost:** none to set up.
**Identity keys:** `wallet.evm.address`, `wallet.solana.address`, `accounts.stripe`, `card.status`

Ordered by how little the human has to do. Everything here is self-custodied: the agent (or the human, if they prefer to hold the key themselves) controls the private key directly, rather than a vendor holding funds on the agent's behalf.

## A wallet the agent actually controls

Generate a keypair locally. No account, no vendor, and the private key never leaves this machine (store it in the secret store, Layer 13, not the identity file).

```bash
# EVM (Ethereum, Base, and any EVM-compatible chain)
node -e "const w=require('ethers').Wallet.createRandom();console.log(JSON.stringify({address:w.address,privateKey:w.privateKey}))"
# Solana
solana-keygen new --no-bip39-passphrase --outfile /dev/stdout --silent 2>/dev/null
```

```bash
python3 humanize.py set wallet.evm.address "<0x...>"
python3 humanize.py secret set wallet.evm.private_key "<0x... the private key>"
```

The human funds the address once, in small amounts, only when something paid is actually needed. Nothing here requires telling a third party who the agent is.

## Pay per request with x402: an open protocol, not a vendor

x402 is an open, multi-chain payment standard (x402.org, maintained by the x402 Foundation, not a single company) built on the HTTP `402 Payment Required` status. A service that speaks it answers a request with a price; the client pays from its own wallet and retries. There is no account with x402 itself, no card, no invoice, because it is a protocol, not a platform.

```bash
pip install x402                      # PyPI, "x402 Payment Protocol SDK for Python", v2.24.0 as of 2026-09-22
# or: npm install @x402/core @x402/evm @x402/svm @x402/fetch
```

Use the local wallet's private key (Layer 13) as the signer the library asks for; read the library's own examples for the exact call shape for the chain in use, since the API differs by network. Check whether a paid service accepts x402 before signing up for anything that charges.

## Get paid: Stripe

Sign up at dashboard.stripe.com/register with the agent's email. Test mode works immediately; store the secret key under `accounts.stripe`. Live payouts need identity and bank details for a person or a Layer 21 entity, which is a human step: prepare everything and hand over the exact page.

## Pay anywhere a card is required

Card networks require a verified person or company behind every card, so the agent cannot get one alone. Two providers describe an agent-facing card flow; neither has been exercised, and one has not even been confirmed reachable, so read this as leads to check, not instructions to follow blind:

- **Stripe Issuing**, once the Stripe account above is live. This is the most established path, since it is the same company as the payout side above.
- **AgentCard** (`npm i -g agentcard`, package 0.3.0): the vendor's own site describes `agentcard signup --email <agent email>`, then the human runs `agentcard setup` once for an identity check and a payment method. The npm package itself ships no README, so this is unconfirmed beyond the marketing page.
- **AgentWallet** (agentwallet.ai): its site describes a KYC step and a card-issuing API, but `api.agentwallet.ai` did not resolve in DNS when checked on 2026-09-21. Do not rely on it until its own docs point at a host that actually answers.

Store only the card token, never the card number. Log every spend with `python3 humanize.py log "<what>" --cost '<amount>'`. Until a card exists, pay with x402 or the wallet directly and report the rest as pending.

> Status (2026-09-22): the local wallet generation is standard and unexercised only in the sense that no real funds have moved through it. `x402` (PyPI, v2.24.0) and the `@x402/*` npm packages are confirmed to exist and are the protocol maintainers' own, documented install path (x402-foundation/x402 on GitHub). The card providers are unverified as described above. See docs/providers.md.
