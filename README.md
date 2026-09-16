# Humanize

A skill that turns an AI agent into a functioning person.

Agents hit walls for boring reasons. They cannot receive a verification email. They cannot get an SMS code. They cannot pay for the thing they need. They cannot sign up anywhere that has no API. Humanize provisions each of those, in order, through APIs, and keeps the result in one identity file so the agent knows what it owns.

## What the agent gets

| Layer | What | Provider | Cost |
|-------|------|----------|------|
| 0 | Name and persona | you | free |
| 1 | Email inbox, send and receive | AgentMail via Orthogonal | $2/mo |
| 2 | Phone number, SMS, voice calls | AgentPhone via Orthogonal | $3/mo per number |
| 3 | WhatsApp | rides on the phone number | varies |
| 4 | Payment card | your issuer, slot ready | varies |
| 5 | A browser it can drive | your host's own browser tools, Notte via Orthogonal as fallback | free or credits |
| 6 | Accounts: GitHub, Vercel, Supabase, any service | sign-up protocol | free |
| 7 | Rules, only if you want them | you | free |

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
| `SKILL.md` | The skill. Layers 0 to 7, commands, costs, identity file schema, and the rules step. |
| `AGENTS.md` | Install, runtime prerequisites, and how to add a new layer or recipe. |
| `README.md` | This file. |

## Roadmap

Card issuer, WhatsApp provider, calendar, and a real mailing address are the next layers. Each one gets added the same way: find it on Orthogonal, run the commands, write the recipe. Pull requests welcome. Read `AGENTS.md` first.

## License

MIT
