# Changelog

## [0.4.1] - 2026-11-08

### Changed
- The card back is now two columns: a larger QR code on the left (bigger modules scan more reliably) and the hint, name, title and contact details on the right. Before, the hint, name, email and wordmark overlapped under the QR, and long payloads pushed the QR tile off the bottom edge. Lines that still do not fit are shrunk, wrapped or trimmed with an ellipsis.

### Fixed
- `humanize.py demo --profile` no longer shows the sample agent's GitHub name.

## [0.4.0] - 2026-11-08

### Added
- Ready-made profiles in `profiles/`: `assistant`, `researcher`, `sales`, `support` and `builder`. `humanize.py init --profile <id>` fills a new identity instantly with the profile's name, persona, business card title and tagline, enabled layers and starting rules; `--name` and `--persona` still win. `humanize.py profiles` lists them and `humanize.py demo --profile <id>` shows one filled in. A profile never overwrites an existing identity.

### Fixed
- `humanize.py card` crashed with `KeyError` on Pillow builds without libraqm (no FriBiDi installed, the default on a fresh Mac). It now falls back to basic text layout; right-to-left text renders unshaped and `docs/troubleshooting.md` says how to get full shaping.
- `card.pdf` is now byte-identical across runs: newer Pillow writes the PDF date as `D:...Z`, which the old pinning pattern missed.
- The Contacts.framework vCard check is skipped off macOS (Linux CI runners have `swift` but not Contacts).

## [0.3.0] - 2026-09-22

### Changed
- The repository is now public.
- **Mailgent is removed.** It was used for the inbox, wallet, vault and calendar, but is not an established, vouched-for product the way AgentMail (YC-backed) and AgentPhone are, and Humanize should not route an agent's inbox, money and vault through a provider nobody can vouch for. AgentMail is now the only, primary email provider; a locally generated wallet, the local secret store, and a local calendar replace what Mailgent used to bundle. See `docs/providers.md` for exactly what was and was not found about it.
- **The DID is removed from Layer 0.** A local `did:key` was attempted as Mailgent's replacement, entirely vendor-free, but the two `openssl` builds this project actually runs on could not reliably generate or sign with an Ed25519 key (LibreSSL cannot generate one at all; OpenSSL 1.1.1 cannot sign with it). Hand-rolling Ed25519 signing without a vetted library was rejected as too risky to ship. Layer 0 is now just a name and a persona.
- Layer 1 (Email) now has one honest human step: AgentMail's own sign-up sends its verification code to a real human email, by design. This is documented as Humanize's one unavoidable human touchpoint, not routed around with a second, unvetted provider.

### Added
- A website in `site/`, deployed on Vercel: what Humanize does, how to use it, the 24 layers with filters, a live avatar generator that recolours the page, the dashboard, security, status and FAQ. Strict CSP, no third-party requests, and tests that check every claim against the repo.
- `scripts/totp.py`: local two-factor codes (RFC 6238 over RFC 4226, standard library only), checked against all five RFC 6238 Appendix B and all ten RFC 4226 Appendix D test vectors.
- `scripts/ical.py`: a local calendar in the standard iCalendar (RFC 5545) format, backed up encrypted alongside memory.
- `humanize.py totp` and `humanize.py calendar` commands.
- `scripts/card.py`, `scripts/vcard.py`, `scripts/qr.py`: business card generator. `python3 humanize.py card` writes `card.vcf`, `front.png`, `back.png` and `card.pdf` to `$HUMANIZE_HOME/card/`. The back carries a QR code (pure-Python ISO 18004 encoder, verified against macOS CoreImage) that saves the agent as a contact when scanned. vCard values are sanitized against injection. Pillow draws the 1050 x 600 px (3.5 x 2 in at 300 dpi) card faces.

### Fixed
- The local calendar module was first written as `scripts/calendar.py` and imported as `import calendar`. That name collides with Python's own standard library `calendar` module: once anything else in the process imports it first (as `urllib.request` does, transitively, and `humanize.py` always does), Python's import cache silently hands back the stdlib module instead, regardless of `sys.path`. `humanize.py calendar add` failed with `AttributeError: module 'calendar' has no attribute 'add'` until this was caught by `tests/test_calendar.py` and the module was renamed to `scripts/ical.py`.

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
