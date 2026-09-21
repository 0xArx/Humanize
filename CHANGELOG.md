# Changelog

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
