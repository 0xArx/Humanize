# Humanize

A skill that turns an AI agent into a functioning person.

Agents hit walls for boring reasons. They cannot receive a verification email. They cannot get an SMS code. They cannot pay for the thing they need. They cannot sign up anywhere that has no API. Humanize provisions each of those, in order, through APIs, and keeps the result in one identity file so the agent knows what it owns. It uses Orthogonal wherever a provider is listed there and goes direct to the vendor everywhere else.

## What the agent gets

| Layer | What | Where it comes from | Human needed |
|-------|------|---------------------|--------------|
| 0 | Name, persona, DID | picked by the agent, DID from Mailgent | no |
| 1 | Email inbox | Mailgent (one empty POST), AgentMail (free, 3 inboxes) | no |
| 2 | Phone, SMS, voice | AgentPhone ($5 credit), Dial (200+ countries, iMessage) | no |
| 3 | WhatsApp, Telegram, Discord, Slack, iMessage | Meta Cloud API, BotFather, Discord and Slack apps, Dial | no |
| 4 | Money: x402 USDC wallet, more wallets, Stripe, a card | Mailgent wallet, local keygen, Stripe, AgentWallet or AgentCard | fund once; card needs one ID check |
| 5 | A browser it can drive | the host's own browser tools, Notte via Orthogonal as fallback | no |
| 6 | Accounts: GitHub, Vercel, Supabase, any service | sign-up protocol with its own inbox and number | no |
| 7 | An avatar: abstract squiggle mark, not a face | `scripts/avatar.py`, local | no |
| 8 | A voice | AgentPhone voice library, ElevenLabs via Orthogonal | no |
| 9 | Eyes on the world: search, scrape, weather, local businesses | Exa, Tavily, Perplexity, Olostep, Openmart, Precip via Orthogonal | Orthogonal key |
| 10 | Its own computer | Smol Machines via Orthogonal, or E2B, Fly.io, Hetzner via GitHub login | no |
| 11 | Memory: notes, people, files | Supabase pgvector, private GitHub repo | no |
| 12 | Brain: extra models | OpenRouter via Orthogonal, or direct keys | Orthogonal key |
| 13 | Passwords, TOTP 2FA, recovery codes | Mailgent vault, which is also the authenticator | no |
| 14 | Social profiles: X, LinkedIn, Reddit, more | sign-up protocol | no |
| 15 | Calendar and a booking page | Mailgent calendar, Cal.com | no |
| 16 | A street address and physical mail | Stable, Earth Class Mail, iPostal1, Lob | notarised form |
| 17 | A domain, a website, email at its own domain | Vercel Domains, Namecheap, AgentMail custom domain | no |
| 18 | E-signatures and documents | Dropbox Sign, DocuSign | no |
| 19 | Verifying other people | Didit via Orthogonal | Orthogonal key |
| 20 | Contacts and people lookup | Hunter, People Data Labs, Apollo, Edges via Orthogonal | Orthogonal key |
| 21 | A legal entity | Stripe Atlas, Firstbase, doola | sign formation docs |
| last | Rules, only if you want them | you | if you want |

Every layer is provisioned step by step: sign up, receive the code, verify, get the token, check the token works, store it. The agent uses its own email and phone for all of this, never yours, so it never has to stop and ask you for a code. The base identity (inbox, phone, avatar, voice, vault, calendar, GitHub, Vercel, Supabase) runs in one session with no input from you and no API key to start: the agent signs itself up for each. The only things it cannot do alone are the ones the law ties to a real person: an identity check for a card, bank details for payouts, a notarised form for a mailbox, signing to form a company.

## Install

**Claude Code**

```bash
git clone https://github.com/0xArx/Humanize.git ~/.claude/skills/humanize
```

Nothing else is needed to start. An Orthogonal key (`ORTHOGONAL_API_KEY`, $10 free on signup) unlocks the world-facing layers: search, scrape, people lookup, extra models.

**Any other agent**

Copy `SKILL.md` into your system prompt or rules file and give the agent a shell with `orth` on it.

## Use

Tell your agent any of these:

- "Humanize yourself."
- "Get yourself an email and a phone number."
- "Sign up for GitHub and get a token."
- "Deploy this to Vercel." (it will provision the account if it has none)
- "Call the dentist and move my appointment."

It reads `~/.humanize/identity.json`, provisions whatever is missing, and gets on with the task.

## Rules are yours to set

Humanize ships with none. When setup finishes the agent asks you one question: do you want any rules? A spend cap, off-limits services, whether it says it is an AI, anything. Whatever you answer is stored in the identity file and followed from then on. Say "none" and it runs with no restrictions.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill. Layers 0 to 21, commands, costs, identity file schema, and the rules step. |
| `AGENTS.md` | Install, runtime prerequisites, and how to add a new layer or recipe. |
| `scripts/avatar.py` | Draws the agent's squiggle avatar from its name. Deterministic, needs only Pillow. |
| `README.md` | This file. |

## Roadmap

Every layer that still needs a person (card, mailbox, entity) gets swapped to an agent-native provider the day one exists. Beyond that: a driver's licence equivalent for age-gated services, ride and delivery apps, banking. Each one gets added the same way: find the provider, run the commands, write the recipe. Pull requests welcome. Read `AGENTS.md` first.

## License

MIT
