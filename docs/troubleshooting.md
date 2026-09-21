# Troubleshooting

Start with `python3 humanize.py doctor`. It checks Python, git, openssl, Node, Pillow, the install, the data folder, the identity file and the dashboard, and `doctor --fix` repairs permissions and missing keys.

## The dashboard

**It did not open, or the address shows "Locked".** The page only opens for its owner. Run `python3 humanize.py open`, which opens it with your access key once and sets a cookie. If you cleared cookies, run it again.

**"port 4242 is busy; using 4243".** Something else holds the port, so it picked the next free one. `python3 humanize.py status` prints the address.

**"The dashboard server is not running" banner.** Run `python3 humanize.py init`. If it exits at once, read `~/.humanize/dashboard.log`.

**"This tab is out of date because the dashboard restarted".** Reload the page.

**Open chat fails.** The button shows the reason. Click Host, pick your app, and press Test. `python3 humanize.py chat` presses the button from a terminal. On Linux the terminal command needs `x-terminal-emulator` or a different command of your choice.

**Fonts look different.** They are bundled and served locally; a blocked request to `/fonts/` would fall back to system fonts. Check the browser console.

**`http://127.0.0.1:4242` says "bad host".** You reached it through another name, a proxy or a tunnel. It answers only to `127.0.0.1`, `localhost` and `[::1]` on its own port, on purpose.

## The identity file

**"identity.json is not valid JSON".** Nothing is overwritten. Your last good copy is `identity.json.bak`: `cp ~/.humanize/identity.json.bak ~/.humanize/identity.json`.

**A key is missing after an update.** `python3 humanize.py doctor --fix` adds keys that newer versions expect, without touching your values.

**Permissions warnings.** `doctor --fix` sets the identity file to 600.

## The avatar

**No PNG.** Pillow could not be installed. Run `python3 humanize.py avatar` and read the message; it installs into `~/.humanize/pydeps` using `pip install --target`, which works even on systems that block system-wide installs. The dashboard draws the avatar live either way.

## The backup

**"No self key".** Set `HUMANIZE_SELF_KEY`, or restore `~/.humanize/self.key`. A new key would make every earlier push unreadable, so none is ever invented on a push.

**"Decrypt failed: wrong self key, or the file was modified".** The key is wrong or the file changed. If the key is lost, the backup cannot be recovered.

**"You have changes that are not pushed".** `self pull` refuses to discard work. Push first, or use `--force` if you mean to throw it away.

**git asks for a password or says authentication failed.** Set `GITHUB_TOKEN` to a token that can read and write the repo (Contents: read and write), or sign git in first. Tokens are passed through the environment and are not stored.

**"git ... failed: repository not found".** The repo does not exist yet, or the token cannot see it. Private repos return "not found" to a token without access.

## The agent

**It asks you for a verification code.** It should not: the code is in its own inbox (Layer 1) or number (Layer 2). Point it at the layer guide.

**A service shows a CAPTCHA.** The agent cannot pass one. It should finish everything else and send you a single message with what is left. See the handoff in `SKILL.md`.

**A sign-up step fails.** Layer guides say how far each provider was verified (`docs/providers.md`). If a real run differs from a guide, the guide is what needs fixing; please report it.

## Platform

Humanize supports macOS and Linux. On Windows use WSL. It needs Python 3.8 or newer.
