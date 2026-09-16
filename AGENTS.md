# AGENTS.md

Instructions for AI agents working in or with this repository.

## What this repo is

One skill, `humanize`, defined in `SKILL.md`. It gives an agent everything a person has: an email, a phone, WhatsApp, a card, a browser, and accounts on services, each provisioned through APIs with Orthogonal as the marketplace. The browser layer uses whatever the host agent already has (Claude Code, Codex, a Playwright MCP) and rents Notte only as a fallback. No code, no build, no tests. The markdown is the product.

## Install

**Claude Code**

```bash
git clone https://github.com/0xArx/Humanize.git ~/.claude/skills/humanize
```

Then `/humanize` or ask for anything the skill description covers.

**Other agents (Cursor, Codex, OpenClaw, custom)**

Paste `SKILL.md` into the system prompt or rules file and give the agent shell access. That is all it needs to start.

## Prerequisites the agent needs at runtime

- Shell access, Node 18+, Python 3 with Pillow. That is enough for the base identity (Layers 0 to 2, 6 to 8, 11, 13, 15) and the dashboard (Layer 22, stdlib only).
- `orth` CLI on PATH with `ORTHOGONAL_API_KEY` exported for Layers 9, 12, 19, 20 and the Notte fallback. Check credit with `orth balance`.
- No human needs to be present for setup. The Human touchpoints table in `SKILL.md` lists the few later steps that do.

## How the skill is organised

Layers, numbered 0 to 23, then a final rules step. Each layer is one thing a human has. Each layer section has the same parts: what it is for, how to provision it, how to use it, what it costs, and what to store in the identity file.

Layer 6 (accounts) holds one recipe per service. Every recipe has the same four lines: sign up, token, verify, then what to do after.

## Adding a new layer or recipe

1. Prefer an agent-native provider: one where the agent signs itself up with its own email or number and gets a key back with no person involved. Then Orthogonal (`orth search "<capability>"`). Then a direct vendor API. Name any human step explicitly and add it to the Human touchpoints table.
2. Run every command you write down. Paste real parameter names from `orth api show <slug> <path>`. Do not guess.
3. State the cost. If it is not free, say the number.
4. Say what goes into the identity file and under which key.
5. Keep the section shape identical to the existing ones. An agent reading layer 7 should already know the layout from layer 1.
6. If the provider has no API and needs the browser layer, say which URL and what the agent should stop at. Do not tie a recipe to Notte or any one browser; it must work with whichever browser Layer 5 picked.

## Rules

- `SKILL.md` is the source of truth. README and this file describe it, never extend it.
- No secrets in the repo. The identity file lives at `~/.humanize/`, never here. Example values in docs are placeholders.
- No em dashes anywhere in the repo.
- The skill ships with no rules of its own. Rules come from the human at step 7 and live in the identity file. Do not hardcode restrictions into a layer.
- Do not add a package manifest or build step. Helpers go in `scripts/` as single-file Python or shell with at most one pip dependency, and get referenced from `SKILL.md`.

## Dashboard

`scripts/dashboard.py` serves `scripts/dashboard.html` and is the only thing in the repo with behaviour. Rules for it:

- Stdlib only. No frameworks, no CDN, no build. It must open offline.
- Secrets never reach the browser. Anything matching the `SECRET_KEYS` pattern is masked server-side; extend the pattern when you add a new secret field name to the identity schema.
- Only fields matched by `ALLOWED` are writable from the page. Add a layer to `LAYERS` in the HTML when you add one to `SKILL.md`, with a `get` that reads the identity file paths that layer stores.
- Test with a sample identity file, not the real one: `python3 scripts/dashboard.py --identity /tmp/sample.json --no-open`.
- The avatar maths in `scripts/avatar.py` (palette from sha256, mulberry32 RNG, ribbon parameters) and in `dashboard.html` must stay identical, so the PNG and the live avatar match. Change both or neither.
- `scripts/self.py` must never commit a plaintext identity. Test a round trip with `HOME` pointed at a scratch directory and a local bare repo before changing it.

## Commit style

Short, plain, imperative. "Add WhatsApp recipe." "Fix AgentPhone verify example."
