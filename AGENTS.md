# AGENTS.md

Instructions for AI agents working in or with this repository.

## What this repo is

One skill, `humanize`, defined in `SKILL.md`. It gives an agent everything a person has: an email, a phone, WhatsApp, a card, a browser, and accounts on services, each provisioned through APIs with Orthogonal as the marketplace. No code, no build, no tests. The markdown is the product.

## Install

**Claude Code**

```bash
git clone https://github.com/0xArx/Humanize.git ~/.claude/skills/humanize
```

Then `/humanize` or ask for anything the skill description covers. Requires the `orth` CLI and `ORTHOGONAL_API_KEY` set.

**Other agents (Cursor, Codex, OpenClaw, custom)**

Paste `SKILL.md` into the system prompt or rules file. Give the agent shell access and the `orth` CLI. That is all it needs.

## Prerequisites the agent needs at runtime

- `orth` CLI on PATH with `ORTHOGONAL_API_KEY` exported. Install: see orthogonal.sh.
- Orthogonal credit balance above zero. Check with `orth balance`.
- Shell access to create `~/.humanize/identity.json`.
- A human reachable for the one-time AgentPhone OTP and for any spend approval.

## How the skill is organised

Layers, numbered 0 to 6. Each layer is one thing a human has. Each layer section has the same parts: what it is for, how to provision it, how to use it, what it costs, and what to store in the identity file.

Layer 6 (accounts) holds one recipe per service. Every recipe has the same four lines: sign up, token, verify, then what to do after.

## Adding a new layer or recipe

1. Search Orthogonal first: `orth search "<capability>"`. If a provider exists, the recipe uses `orth run`, not raw curl.
2. Run every command you write down. Paste real parameter names from `orth api show <slug> <path>`. Do not guess.
3. State the cost. If it is not free, say the number and say "ask before buying".
4. Say what goes into the identity file and under which key.
5. Keep the section shape identical to the existing ones. An agent reading layer 7 should already know the layout from layer 1.
6. If the provider has no API and needs the browser layer, say which URL and what the agent should stop at.

## Rules

- `SKILL.md` is the source of truth. README and this file describe it, never extend it.
- No secrets in the repo. The identity file lives at `~/.humanize/`, never here. Example values in docs are placeholders.
- No em dashes anywhere in the repo.
- Do not remove a guardrail without an issue explaining why.
- Do not add a dependency, script, or package manifest. If the skill needs a helper, it goes in `scripts/` as a plain shell file and gets referenced from `SKILL.md`.

## Commit style

Short, plain, imperative. "Add WhatsApp recipe." "Fix AgentPhone verify example."
