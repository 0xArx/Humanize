# Humanize

A skill that turns an AI agent into a functioning person.

Agents hit walls for boring reasons. They cannot receive a verification email. They cannot get an SMS code. They cannot pay for the thing they need. They cannot sign up anywhere that has no API. Humanize provisions each of those, in order, through APIs, and keeps the result in one identity file so the agent knows what it owns. It uses Orthogonal wherever a provider is listed there and goes direct to the vendor everywhere else.

## What the agent gets

| Layer | What | Where it comes from |
|-------|------|---------------------|
| 0 | Name and persona | you |
| 1 | Email inbox, send and receive | AgentMail via Orthogonal, $2/mo |
| 2 | Phone number, SMS, voice calls | AgentPhone via Orthogonal, $3/mo per number |
| 3 | WhatsApp, Telegram, Discord, Slack, iMessage | Meta Cloud API, BotFather, Discord and Slack apps |
| 4 | Money: a card, Stripe to get paid, a crypto wallet | Stripe Issuing or Lithic, Stripe, local keygen |
| 5 | A browser it can drive | your host's own browser tools, Notte via Orthogonal as fallback |
| 6 | Accounts: GitHub, Vercel, Supabase, any service | sign-up protocol |
| 7 | A face: profile photo and video replica | Nano Banana, Tavus via Orthogonal |
| 8 | A voice, the same on calls and voice notes | ElevenLabs via Orthogonal |
| 9 | Eyes on the world: search, scrape, weather, local businesses | Exa, Tavily, Perplexity, Olostep, Openmart, Precip via Orthogonal |
| 10 | Its own computer | Smol Machines via Orthogonal, or Fly.io, Hetzner, E2B, AWS |
| 11 | Memory: notes, people, files | Supabase pgvector, private GitHub repo |
| 12 | Brain: extra models | OpenRouter via Orthogonal, or direct keys |
| 13 | Passwords, TOTP 2FA, recovery codes | identity file or Bitwarden, oathtool |
| 14 | Social profiles: X, LinkedIn, Reddit, more | sign-up protocol |
| 15 | Calendar and a booking page | Google Calendar, Cal.com |
| 16 | A street address and physical mail | Stable, Earth Class Mail, iPostal1, Lob |
| 17 | A domain, a website, email at its own domain | Vercel Domains, Namecheap, AgentMail custom domain |
| 18 | E-signatures and documents | Dropbox Sign, DocuSign |
| 19 | Verifying other people | Didit via Orthogonal |
| 20 | Contacts and people lookup | Hunter, People Data Labs, Apollo, Edges via Orthogonal |
| 21 | A legal entity | Stripe Atlas, Firstbase, doola |
| last | Rules, only if you want them | you |

Every layer is provisioned step by step: sign up, receive the code, verify, get the token, check the token works, store it. The agent uses its own email and phone for all of this, never yours.

## Install

**Claude Code**

```bash
git clone https://github.com/0xArx/Humanize.git ~/.claude/skills/humanize
```

You also need the Orthogonal CLI with `ORTHOGONAL_API_KEY` set. Every provider in this skill is reached through it.

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
| `README.md` | This file. |

## Roadmap

Every layer that currently points at a vendor with no Orthogonal wrapper (card issuer, WhatsApp, virtual mailbox, e-sign) gets swapped to `orth run` the day one appears. Beyond that: a driver's licence equivalent for age-gated services, ride and delivery apps, banking. Each one gets added the same way: find the provider, run the commands, write the recipe. Pull requests welcome. Read `AGENTS.md` first.

## License

MIT
