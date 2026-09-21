---
name: humanize
description: Give an AI agent everything a person has, one step at a time: an email inbox, a phone number with SMS and voice, a wallet, accounts and 2FA, an avatar and voice, local memory, a machine of its own, a dashboard to watch and steer it, and an encrypted private repo so it can be loaded on any machine. Prefers services an agent can sign itself up for, then free local tools, and names the few steps that need a person. Use when the user says humanize, or the agent needs an inbox, a phone number, an OTP, an account, a wallet, a token, memory, or to be set up on a new machine.
---

# Humanize

An agent without an inbox cannot receive a verification code. Without a phone it cannot pass an OTP or take a call. Without a wallet it cannot pay. Without accounts it cannot deploy or store anything. Without memory it forgets. Humanize closes those gaps one layer at a time, keeps everything in one identity file, and gives the human a dashboard to see and steer it.

Run every command from the folder this file is in. New here: `python3 humanize.py init` creates the identity, draws the avatar and opens the dashboard. Something odd: `python3 humanize.py doctor`.

## How to work

At the start of every turn, and after every provisioning step (details in [Layer 22](layers/22-dashboard.md)):

1. `python3 humanize.py requests` lists what the human typed into the dashboard. Do each one, then `python3 humanize.py done <index>`.
2. A layer the human switched off is not used: `python3 humanize.py get layers.<n>.enabled` prints `false`. Do not send from that inbox, call from that number or post to that network until it is on again. Off is not deleted.
3. The human may have changed `name`, `persona` or `rules`. Read them with `get` and apply them.
4. Read before you provision. `python3 humanize.py status` and `get <path>` show what already exists, so nothing is bought twice.
5. Write down what you did: `python3 humanize.py log "<what>" [--cost '<amount>']`, then `python3 humanize.py self push` once the agent has a backup repo.

## The identity file

Everything the agent owns lives in `~/.humanize/identity.json` (mode 600). Never edit it by hand: the dashboard writes to it too. Use `get`, `set`, `log`, `requests` and `done`, which lock the file so no edit is lost. `set` keeps text as text and parses booleans and lists where a key expects them (`set rules '["no spend over 50"]'`, `set layers.14.enabled false`); it refuses a value of the wrong type, and `--json` forces JSON. `identity.template.json` lists every key.

Secrets never sit in that file. `set` sends any key that looks like a secret (`api_key`, `token`, `password`, `privateKey` and so on) to the machine's secret store, the macOS Keychain or the Linux keyring, and leaves a pointer such as `secret:email.mailgent.api_key` behind. `get` fetches the real value for you, so nothing else changes. Passwords, 2FA secrets and account tokens go in the Mailgent vault ([Layer 13](layers/13-keys-2fa.md)). That leaves one small set of keys in the secret store: the ones the agent needs to reach the vault and its services. `python3 humanize.py secret list` shows what is stored, and `doctor` warns if anything is left as plain text.

## Choosing a provider

In this order. Take the first that works.

1. **Agent-native.** The agent signs itself up with one API call and no person: Mailgent, AgentMail, AgentPhone.
2. **Free and keyless.** A local tool or a public API with no account.
3. **One signup that replaces many.** Apify (thousands of scrapers, one token), OpenRouter (hundreds of models, one key), the x402 Bazaar (paid APIs with no signup at all, paid from the agent's wallet).
4. **A single vendor's account.** Last resort.

Before adding any provider, ask whether the agent can get it alone with its own email and number. If it cannot, say so and name the human step.

## The layers

| # | Layer | Gives the agent | A person is needed for |
|---|-------|-----------------|------------------------|
| 0 | [Identity](layers/00-identity.md) | a name, a persona, a DID | nothing |
| 1 | [Email](layers/01-email.md) | inboxes to read and send from | nothing |
| 2 | [Phone](layers/02-phone.md) | a number for SMS, OTPs and calls | nothing |
| 3 | [Messaging](layers/03-messaging.md) | Slack, Telegram, Discord, WhatsApp, iMessage | Discord and WhatsApp, maybe Telegram |
| 4 | [Money](layers/04-money.md) | an x402 wallet, Stripe, a card | funding once, a card's ID check |
| 5 | [Browser](layers/05-browser.md) | hands, for services with no API | a CAPTCHA, when one appears |
| 6 | [Accounts](layers/06-accounts.md) | GitHub, Vercel, Supabase, any service | the GitHub CAPTCHA, once |
| 7 | [Avatar](layers/07-avatar.md) | a mark unique to this agent | nothing |
| 8 | [Voice](layers/08-voice.md) | one voice for calls and notes | nothing |
| 9 | [Eyes](layers/09-eyes.md) | search, page reading, weather, places | funding, only for paid lookups |
| 10 | [Computer](layers/10-computer.md) | a machine of its own | a card, only for a cloud machine |
| 11 | [Memory](layers/11-memory.md) | searchable notes and people | nothing |
| 12 | [Brain](layers/12-brain.md) | other models to call | nothing locally |
| 13 | [Keys and 2FA](layers/13-keys-2fa.md) | a vault and an authenticator | nothing |
| 14 | [Social](layers/14-social.md) | public profiles | a CAPTCHA per network |
| 15 | [Calendar](layers/15-calendar.md) | a calendar and a booking page | nothing |
| 16 | [Address](layers/16-address.md) | a street address and mail | a notarised form |
| 17 | [Domain](layers/17-domain.md) | a domain, a site, its own email | a card |
| 18 | [Signatures](layers/18-signatures.md) | documents it can fill and sign | maybe an identity check |
| 19 | [Verify others](layers/19-verify.md) | checks that a phone or email is real | nothing |
| 20 | [Contacts](layers/20-contacts.md) | people it knows and can find | nothing |
| 21 | [Entity](layers/21-entity.md) | a company, if needed | a signature |
| 22 | [Dashboard](layers/22-dashboard.md) | a window for the human, and the chat button | nothing |
| 23 | [Self, stored](layers/23-self-storage.md) | an encrypted backup, loadable anywhere | a git remote and token; keeping the key |

## What needs a person

The agent does everything else itself, including every verification code, because the code is always in its own inbox or number. These are the only human steps, and each is reached only when its layer is wanted:

| When | What the person does | Why the agent cannot |
|------|----------------------|----------------------|
| Any CAPTCHA | Clicks through it | Agents cannot pass them, and most sign-up terms forbid automated accounts |
| GitHub, X, Reddit, LinkedIn, Discord | Creates the account from details the agent prepared | CAPTCHA and terms of service |
| A backup repo | Makes an empty private repo and a token limited to it, or a GitHub account for the agent | Same as above |
| A paid lookup or service | Sends USDC to the agent's wallet once | Money has to come from somewhere |
| A card | One identity check with the issuer | Card networks require a verified person |
| Stripe payouts | Identity and bank details | The account holder must be a legal person |
| A virtual mailbox | Signs and notarises a USPS form | A federal requirement |
| A company | Signs the formation papers | The owner must be a person |
| The end of setup | Says which rules, if any, to follow | Only they know |

## One-shot bootstrap

**Phase A: no person needed.** Every step is agent-native or local.

1. Pick a name and persona and check the handle ([Layer 0](layers/00-identity.md)).
2. `python3 humanize.py init --name "<name>" --persona "<persona>"`. The dashboard is now open for the human to watch.
3. Mailgent sign-up: inbox, DID, vault, calendar, wallet ([Layer 1](layers/01-email.md)).
4. AgentMail sign-up with the Mailgent address as the human email, read the code, verify. Skip it if it refuses that domain.
5. AgentPhone sign-up with the agent's own email, read the code, verify, store the key and number ([Layer 2](layers/02-phone.md)).
6. Pick an AgentPhone voice and a local voice ([Layer 8](layers/08-voice.md)).
7. Record the free tools and the browser, make an SSH key, write a first memory ([Layers 9, 5, 10, 11](layers/09-eyes.md)).
8. Check the calendar works ([Layer 15](layers/15-calendar.md)).

The agent now has an inbox, a number, a wallet, a DID, a vault, a calendar, an avatar, a voice, memory and a dashboard, at no cost and with nobody's help.

**Phase B: one handoff, batched into a single message.** Do not drip questions. Prepare everything, then send the human one message like this:

> Setup so far is done, and it is all on the dashboard. To finish I need about five minutes from you:
> 1. **A place to keep me.** Either make an empty private GitHub repo and a fine-grained token limited to it (Contents: read and write), or create a GitHub account for me from these details: username `<u>`, email `<e>`, password (in my vault), avatar at `<path>`. GitHub needs a person for the CAPTCHA.
> 2. **Optional, only when you want it.** My wallet address is `<0x...>` if you want me to be able to pay for things.
> Send me the repo URL and token when you have them.

**Phase C: the agent again.** Run `python3 humanize.py self init <repo url>` and hand the human the self key it prints, once ([Layer 23](layers/23-self-storage.md)). After that, provision layers as tasks need them: Vercel and Supabase through "Continue with GitHub", a booking page, messaging, and so on.

## The last question

When Phase A and the backup are done, ask the human once, and do not block on the answer:

> Setup is done. Do you want any rules for how I use this identity? For example a spending cap, services I should stay away from, or whether I say I am an AI when asked. Say "none" to skip.

Whatever they answer, now or later, goes into `rules` (`python3 humanize.py set rules '["..."]'`, or they type it on the dashboard) and is followed from then on. If they say nothing, there are no rules beyond what they ask for in the moment. Humanize ships with none.

## When something goes wrong

`python3 humanize.py doctor` checks the machine and the install and `doctor --fix` repairs what it can. The dashboard log is `~/.humanize/dashboard.log`. See [docs/troubleshooting.md](docs/troubleshooting.md), and [docs/providers.md](docs/providers.md) for how far each provider's instructions have been verified.
