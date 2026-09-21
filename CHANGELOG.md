# Changelog

## [0.2.0] - 2026-09-21

### Added
- Secrets no longer sit in the identity file. Keys that look like secrets are stored in the macOS Keychain (or the Linux keyring, or a private file where neither exists) and replaced by pointers. `humanize.py get` fetches them, `set` stores them, and `secret list|get|set|delete|migrate|backend` manage them.
- The self key lives in the same store. The encrypted backup now carries the secrets and restores them on a new machine.
- `doctor` warns about plain-text secrets and missing ones, and `--fix` migrates them.

### Fixed
- Local calls no longer go through a system proxy, the server no longer waits on a reverse DNS lookup, and `set` keeps text as text.

## [0.1.0] - 2026-09-21

First release.

### Added
- `SKILL.md` and 24 layer guides: identity, email, phone, messaging, money, browser, accounts, avatar, voice, eyes, computer, memory, brain, keys and 2FA, social, calendar, address, domain, signatures, verifying others, contacts, entity, dashboard, self-storage.
- `humanize.py`: `init`, `open`, `status`, `doctor`, `stop`, `dashboard`, `demo`, `avatar`, `self`, `memory`, and `get`, `set`, `log`, `requests`, `done`, `chat` for agents.
- A full-page local dashboard: live avatar, overview, filterable layer grid with switches, detail drawer, request composer, activity, rules, backup status, host picker for the chat button, light and dark themes, and no third-party requests.
- A deterministic avatar of flowing ribbons derived from a seed, drawn identically by Python and by the dashboard.
- Local memory: notes and people in one SQLite file with full-text search.
- An encrypted backup of the agent to a private git repo, loadable on any machine.
- A test suite covering the dashboard's attack surface, locking, the backup, the avatar, and the docs.

### Security
- The dashboard is hardened against cross-site request forgery, DNS rebinding, other local users, script injection and oversized or malformed input. See `SECURITY.md`.
