# Architecture

## The parts

```
   the human                         the agent
       |                                 |
   dashboard (browser)             SKILL.md + layers/*.md
       |  localhost only                 |  follows the guides
       v                                 v
   scripts/dashboard.py  <------>  humanize.py  (get, set, log, requests, done, chat, memory ...)
              \                         /
               v                       v
             scripts/store.py   (locked, atomic reads and writes)
                      |
                      v
            $HUMANIZE_HOME  (default ~/.humanize)
            identity.json   memory.db   face.png   self.key   dashboard.key   dashboard.json
                      |
                      v  scripts/self.py  (encrypt, commit, push)
              a private git repo  ->  loaded on any machine
```

Nothing here is a server you deploy. The dashboard is a small standard-library HTTP server on the loopback interface, started in the background by `humanize.py init`.

## The data folder

`$HUMANIZE_HOME`, default `~/.humanize`, mode 700.

| File | What it is | Mode |
|------|------------|------|
| `identity.json` | Everything the agent owns. Schema is `identity.template.json`. | 600 |
| `identity.json.bak` | The previous version, kept on every write. | 600 |
| `memory.db` | Notes and people, SQLite with full-text search. | 600 |
| `face.png` | The avatar, drawn from `face.seed`. | 644 |
| `self.key` | The self key, so unattended pushes work. | 600 |
| `self/` | The working copy of the backup repo. | |
| `self.state.json` | The fingerprint of what was last pushed. | 600 |
| `dashboard.key` | The owner's access key for the dashboard, stable across restarts. | 600 |
| `dashboard.json` | The running dashboard's pid, port and per-run token. Removed on exit. | 600 |
| `dashboard.log` | The dashboard's output. | 644 |
| `pydeps/` | Pillow, installed on demand. | |

## The identity file

One JSON object. The template lists every key, empty. Groups:

- Who: `name`, `persona`, `did`, `face`.
- Reach: `email`, `phone`, `messaging`, `whatsapp`, `calendar`, `address`, `domain`.
- Money: `wallet`, `card`, `entity`.
- World: `browser`, `accounts`, `eyes`, `computer`, `ssh`, `memory`, `brain`, `social`, `verify`, `contacts`, `voice`.
- Control: `layers.<n>.enabled`, `rules`, `dashboard_requests`, `host`, `self_repo`.
- Record: `log`, capped at 1000 entries.

Service API keys live here. Passwords, TOTP secrets and account tokens live in the Mailgent vault with a pointer here.

## Concurrency

The dashboard, the agent's `humanize.py` calls and `self.py` all write the identity file. `store.update` takes an exclusive `flock` on `identity.json.lock`, reads, applies the change, writes a temp file, fsyncs and renames it into place. Two processes therefore never lose each other's edits; `tests/test_store.py` proves it with threads and with processes.

## The dashboard

`scripts/dashboard.py` serves `scripts/dashboard.html`, `scripts/orb.js` and the bundled fonts.

| Route | Auth | Purpose |
|-------|------|---------|
| `GET /` | owner cookie, or `?k=<access key>` once | The page, with the per-run token and a CSP nonce injected. |
| `GET /orb.js`, `/fonts/*` | host check only | Static, no secrets. |
| `GET /api/ping` | host check only | Lets `humanize.py` tell whether a port is a Humanize dashboard. |
| `GET /avatar` | owner cookie | The avatar PNG. |
| `GET /api/identity` | token | The identity, masked, plus `seed`, `mtime`, `version`. |
| `GET /api/self/status`, `POST /api/self/push` | token | Backup state and push. |
| `POST /api/update` | token | Write one whitelisted field. |
| `POST /api/request`, `/api/request/done` | token | Requests to the agent. |
| `POST /api/chat` | token | Run `host.open_command`. |

The page polls `/api/identity` every three seconds and re-renders when the file's mtime changes.

## The avatar

`avatar.params(seed)` and `HZ.orbParams(seed)` derive, from `sha256(seed)`: four hues with a spread and a complement, a saturation, and 4 to 6 ribbons each with two sine components, a tilt, widths and a drift, drawn from a seeded `mulberry32` in a fixed order. Python renders a PNG from them with Pillow; the dashboard animates the same ribbons on a canvas. The test compares the two derivations for several seeds to 1e-9.

## The backup

`self.py` writes `identity.json.enc` and, if present, `memory.db.enc` (a consistent SQLite snapshot). File format: `HZ1` + the output of `openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt` + a 32 byte HMAC-SHA256 over everything before it. The AES key comes from openssl's PBKDF2 over the self key; the HMAC key is a separate PBKDF2 derivation with a fixed domain-separation salt. The repo also carries a copy of `scripts/`, `humanize.py`, the template, and the avatar, so a machine can boot from the backup alone.

Sync state is a fingerprint (SHA-256 of the identity without `self_repo`) stored in `self.state.json`. It is what lets the dashboard show "unpushed changes" and lets `pull` refuse to discard them.
