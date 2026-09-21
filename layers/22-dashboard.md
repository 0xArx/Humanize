# Layer 22: Dashboard

**Gives the human:** a window into the agent and a way to steer it. A local web page, nothing leaves the machine.
**Human needed:** none. **Cost:** free.
**Identity keys:** `host.app`, `host.open_command`, `host.chat_url`, `host.session_id`, `layers.<n>.enabled`, `dashboard_requests`, `rules`

```bash
python3 humanize.py init          # creates the identity if missing, starts the dashboard in the background, opens it
python3 humanize.py status        # is it up, what does the agent have
python3 humanize.py open          # open it in the browser again (the address alone will show a locked page)
python3 humanize.py stop
python3 humanize.py dashboard     # run in the foreground instead
python3 humanize.py demo          # a filled sample agent in a scratch folder, to see it without touching the real one
python3 humanize.py doctor        # check the machine and the install
```

Start it as soon as the identity exists so the human can watch layers fill in during setup. It is standard-library Python, keeps running across sessions, and picks another port if 4242 is busy.

## What it shows

The live avatar, name and persona (editable in place). Copy rows for the email, number, wallet and handles. A KPI strip. Every layer as a card with its status, its facts, an on/off switch and a Provision or Modify button, filterable and searchable; click a card for its full details. A box to send the agent a request. Requests, activity and rules in tabs. The state of the encrypted backup with a Push button. Secrets are hidden before they reach the browser and are never editable there.

## The chat button

Open chat runs `host.open_command` on this machine, and opens `host.chat_url` in the browser if that fails. If the command fails the button shows why instead of staying silent. `init` detects a sensible default, the Host button lets the human pick and test another, and the agent can set them:

| Host | `host.app` | `host.open_command` | `host.chat_url` |
|------|------------|---------------------|-----------------|
| Claude Code, desktop app | `claude-code-desktop` | `open -a "Claude"` (macOS) | |
| Claude Code, terminal | `claude-code-terminal` | `osascript -e 'tell app "Terminal" to do script "cd <project> && claude --resume <session_id>"'` (macOS); `x-terminal-emulator -e claude --resume <session_id>` (Linux) | |
| Claude Code, web | `claude-code-web` | | the session URL |
| Codex CLI | `codex` | `osascript -e 'tell app "Terminal" to do script "cd <project> && codex resume <session_id>"'` | |
| Cursor | `cursor` | `open -a Cursor` | `cursor://` |
| VS Code | `vscode` | `open -a "Visual Studio Code"` | `vscode://` |

```bash
python3 humanize.py set host.session_id "<id>"
python3 humanize.py chat          # presses the button, so you can test it
```

## How the agent uses it

Never edit `~/.humanize/identity.json` by hand: the dashboard writes to it too, and the helpers below take a lock so no edit is lost. At the start of every turn, and after every provisioning step:

```bash
python3 humanize.py requests                 # what the human typed, as JSON with an index; do each, in order
python3 humanize.py done <index>             # when finished
python3 humanize.py get layers.14.enabled    # prints "false" if the human switched that layer off
python3 humanize.py get rules
python3 humanize.py get name
python3 humanize.py log "created telegram bot"
```

1. Do every pending request, then mark it done.
2. A layer switched off is not used: do not send from that inbox, call from that number or post to that network until it is switched back on. Do not delete anything; off is not gone.
3. The human may have edited `name`, `persona` and `rules` on the page. Apply them from now on. If the name changed, update display names and bios everywhere.
4. Log what you did, so the page tells the truth.

The page refreshes every three seconds, so anything the agent writes appears without a reload.

## How it protects itself

It listens on 127.0.0.1 only, serves the page only to a browser holding the owner's access key (so another user on the same machine cannot load it), answers only requests addressed to itself, refuses requests that came from another website, needs a per-run token for every call, validates and size-limits what it accepts, and runs under a strict content security policy with no third-party requests. See SECURITY.md.
