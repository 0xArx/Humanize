# Security

Humanize holds an agent's keys and can run a command on your machine, so its threat model is written down.

## What is protected, and how

| Asset | Where it lives | Protection |
|-------|----------------|------------|
| Identity file (addresses, pointers) | `~/.humanize/identity.json` | Mode 600 in a mode 700 folder. Written atomically under a lock, with a `.bak` of the previous version. Never committed (`.gitignore`). Holds pointers such as `secret:email.mailgent.api_key`, not secrets. |
| The agent's own service keys (Mailgent, AgentMail, AgentPhone, tokens) | The macOS Keychain, or the Linux keyring, or a mode 600 file where neither exists | Any key whose name looks like a secret is moved there automatically. `doctor` warns about anything left in plain text, and `secret migrate` moves it. |
| Passwords, TOTP secrets, account tokens | The Mailgent vault (AES-256-GCM at rest, per the vendor) | The identity file holds only a pointer. |
| Memory | `~/.humanize/memory.db` | Mode 600. |
| The dashboard's power to run a command | `scripts/dashboard.py` | See below. |
| The backup repo | A private git repo | Identity and memory are encrypted before commit. See below. |
| The self key | The same secret store, and with the human | Shown once. Cannot be recovered. |

## The dashboard

It can run `host.open_command`, so a web page you happen to visit must not be able to drive it, and neither should another user of the same machine. Every layer below is covered by a test in `tests/test_dashboard.py`.

- Listens on `127.0.0.1` only, never on a network interface.
- **Host check:** answers only requests whose `Host` is `127.0.0.1`, `localhost` or `[::1]` on its own port, which defeats DNS rebinding.
- **Origin and Sec-Fetch-Site checks:** refuses requests that came from another site.
- **Owner-only page:** the page, and so the token inside it, is served only to a browser that presents the owner's access key (`~/.humanize/dashboard.key`, mode 600) once, which is exchanged for an `HttpOnly`, `SameSite=Strict` cookie. Another user on the machine can reach the port but cannot read the key file.
- **Per-run token** on every `/api` call, sent in a custom header, which also forces a CORS preflight that the server never grants.
- **JSON only:** POST bodies must be `application/json`, at most 64 KB, and every writable field is validated by type and range. Only a short list of fields can be written from the browser, and none of them are secrets.
- **Strict CSP with a per-response nonce:** `default-src 'none'`, no inline event handlers, no third-party requests, no framing. Every value shown is escaped. Fonts and scripts are served from the same origin.
- **Secrets are masked** by key name before they leave the server, with no exemptions.
- **Static routes** are whitelisted by pattern and folder; the avatar route serves only small files with a real image signature.
- Errors are returned as short messages, never tracebacks.

The first version of this dashboard did not do these, and a web page could run commands on your machine through it. That is fixed, and the exact attack is a regression test.

## The encrypted backup

`identity.json`, the secrets it points at, and `memory.db` are encrypted with AES-256-CBC. The key is derived from the self key with PBKDF2-HMAC-SHA256 (200,000 rounds, a random salt per file), and the ciphertext is sealed with an HMAC-SHA256 under a separate derived key, checked before decryption, so a wrong key or a modified file is refused rather than decrypted into garbage. The passphrase reaches openssl through a private temporary file, not the command line. The git token reaches git through environment variables, so it is not in the process list or in `.git/config`. `self pull` will not overwrite local work that was never pushed.

## What is not protected

Be clear about these limits.

- **Anyone with your user account, or malware running as you,** can read `~/.humanize`. File modes stop other users, not you.
- **The agent itself** holds the keys it needs. Humanize does not sandbox it. Use the on/off switches and rules to constrain what it does.
- **The secret store protects secrets at rest, not from the agent.** The agent has to read them to use them, and anything running as you can ask the Keychain for an item that the `security` tool created. macOS may ask you the first time. Isolation, meaning a separate user account or a container for the agent, is the only real fix for that.
- **Where there is no system secret store** (a headless Linux server without a keyring) secrets fall back to a mode 600 file, in plain text. `doctor` says so.
- **Writing a secret to the macOS Keychain passes it to the `security` tool as an argument,** so another account on the same Mac could see it in the process list for a few milliseconds. Reads do not have this problem. This matters only on a Mac shared with people you do not trust.
- **Third parties.** Mailgent, AgentMail, AgentPhone, Dial, Apify and the others see what you send them. Their command line tools are npm packages that run on your machine: install only the ones you mean to use.
- **Plain HTTP on localhost.** There is no TLS, which is normal for a loopback-only server, and is why the access key and cookie exist.
- **A lost self key** makes the backup unreadable, by design.

## Reporting a problem

The repository is private. Open a private security advisory on the repository, or contact the owner, 0xArx, on GitHub. Please include what you did and what happened. Fixes ship with a regression test.
