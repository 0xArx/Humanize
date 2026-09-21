# AGENTS.md

For AI agents that work in this repository, and for agents that use it.

## Using Humanize as an agent

Start at `SKILL.md`. It is short on purpose: it tells you how to work each turn, which provider to prefer, which layer guide to open, and which steps need a person. Open a guide in `layers/` only when you need that layer. Never edit `~/.humanize/identity.json` by hand; use `humanize.py get`, `set`, `log`, `requests` and `done`.

Installing it as a skill:

| Host | How |
|------|-----|
| Claude Code | `install.sh` links this folder to `~/.claude/skills/humanize`, or `ln -s ~/.humanize/app ~/.claude/skills/humanize`. Then `/humanize` or just ask. |
| Codex, Cursor, Windsurf, Cline, OpenClaw | This file and `SKILL.md` are plain markdown. Point the agent at `~/.humanize/app/SKILL.md`, or paste it into the rules file. Give it a shell. |
| Any chat model with a shell | Paste `SKILL.md` and let it open the layer files it needs. |

## Working on this repository

The product is markdown plus a handful of small Python and JavaScript files. Standard library only: no package manifest, no build step, no dependency to install. The only optional third-party code is Pillow, installed on demand into the user's `~/.humanize/pydeps` for the avatar PNG.

### Before you finish any change

```bash
python3 -m unittest discover -s tests
```

It must pass. A bug fix ships with a test that fails without it. Tests use a throwaway `HUMANIZE_HOME`; never point one at the real `~/.humanize`.

### Rules

- **No em dashes** anywhere. `tests/test_repo.py` enforces it.
- **No third-party requests from the dashboard.** No CDN, no analytics, no fonts fetched from the network. Fonts are bundled.
- **No inline event handlers** in `scripts/dashboard.html`. It runs under a strict CSP. Use `data-act` attributes and the delegated listeners, and escape every value with `esc()`.
- **The avatar maths must stay identical** in `scripts/avatar.py` (`params`) and `scripts/orb.js` (`orbParams`), including the order of random draws. `tests/test_avatar_parity.py` compares them for several seeds. Change both or neither.
- **Secrets never reach the browser.** `store.mask` hides any value under a secret-looking key. When you add a key whose name does not match, extend `_SECRET` and add a test.
- **Only fields listed in `WRITABLE` in `scripts/dashboard.py` can be written from the browser**, each with a type check. Keep that list short.
- **Every writer uses `scripts/store.py`** (locked, atomic, with a `.bak`). Do not write the identity file any other way.
- **`self.py` must never commit a plaintext identity or memory.** Test a round trip with a local bare repo before changing it.
- **The identity template is the schema.** A new identity key goes in `identity.template.json`, and in the dashboard's `LAYERS` if a layer should show it. `doctor --fix` adds new keys to existing identities.
- **No secrets in the repo**, including examples. `tests/test_repo.py` scans for common key shapes.
- **Commits** are made under your own name, with no attribution trailers, in short plain imperative sentences.

### Writing or changing a layer guide

A guide in `layers/NN-name.md` opens with `# Layer N: Title`, then the same fields the others have: what it gives the agent, whether a person is needed, what it costs, and which identity keys it uses. Then the steps.

1. Prefer a service the agent can sign itself up for with its own email and number. Then a free local tool or keyless API. Then one signup that replaces many. A single vendor's account is last.
2. **Read the vendor's own docs and run what you can.** Paste real endpoints and flags. Do not guess field names. If the docs do not say, say so in the guide.
3. State the cost. If it is not free, give the number.
4. Name every human step. If a CAPTCHA, an identity check or a legal signature is involved, say so, and never present a service as agent-only when it is not.
5. Add a dated line to `docs/providers.md` saying what you checked and how, and end the guide with a short status note that matches it.
6. Update the layer tables in `SKILL.md` and `README.md` if a layer's human-needed column changes.

### Layout

See the tree in `README.md`. `docs/architecture.md` explains how the parts fit.
