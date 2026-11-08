# Providers: what was checked

The layers cite real services. This page says how far each citation has been verified, so nobody has to guess. Dates are when the check was made.

**Levels**

- **Read:** the vendor's own documentation or source was read and the endpoint, package or command matches.
- **Reachable:** the host or package answered (an HTTP status, or `npm view`, or PyPI).
- **Exercised:** we ran it end to end.

No live sign-up has been exercised. Signing up creates a real account, so that is left for a real run.

## Removed

**Mailgent.** Used through 2026-09-21 as the primary email, wallet, vault and calendar provider. Removed on 2026-09-22 at the project owner's direction: it is not a known, established product the way AgentMail (YC-backed) or AgentPhone are, and Humanize should not route an agent's inbox, money and vault through a provider nobody can vouch for. To be precise about what was and was not found: `api.mailgent.dev` did answer (401 to an unauthenticated request, meaning the host is up) and `@mailgent-dev/cli` 0.7.1 existed on npm when checked; no technical fault was found in Mailgent's own service, because its sign-up was never exercised, same as every other provider on this page. The removal is a trust decision, not a bug report, and it is recorded here so the reasoning is not lost. AgentMail (below) replaces it for email; a locally generated, self-custodied wallet replaces its wallet; the machine's own secret store plus local TOTP (below) replace its vault; a local iCalendar file replaces its calendar.

**A locally generated "DID" for Layer 0.** This one *was* a genuine technical failure, unrelated to the Mailgent decision above, found while building a replacement. The plan was a `did:key` (Ed25519, W3C spec) generated with `openssl`, no vendor at all. Tested on 2026-09-22 against the two `openssl` binaries actually present on the machines this runs on:

- macOS's own `/usr/bin/openssl` is LibreSSL 3.3.6, which refuses `genpkey -algorithm ed25519` outright ("Algorithm ed25519 not found").
- OpenSSL 1.1.1l (a common version from package managers) can generate the key but its `pkeyutl` cannot sign with it at all ("operation not supported for this keytype"); Ed25519 signing via the generic `EVP_PKEY_sign` path is an OpenSSL 3.0-and-later feature.

Reimplementing Ed25519 signing by hand, in pure Python, with no vetted library, was rejected on purpose: that is real cryptographic code, and shipping a hand-rolled version without a security review is worse than not having the feature. The DID was dropped from Layer 0 rather than shipped broken. See [layers/00-identity.md](../layers/00-identity.md).

## Current

| Provider | Used for | Read | Reachable | Exercised | Notes |
|----------|----------|------|-----------|-----------|-------|
| AgentMail | The agent's inbox (Layer 1) | `POST /v0/agent/sign-up` and `/v0/agent/verify` pages, with request and response fields | `agentmail` on npm 0.5.27 and PyPI; `api.agentmail.to` reachable | No | Sign-up sends its OTP to the human's real email, by design; this is now documented as Humanize's one unavoidable human step, not routed around. Sign-up is idempotent and rotates the key. |
| AgentPhone | Number, SMS, voice (Layer 2) | Its skills page: sign-up, verify, calls, messages, voices, verify endpoints and pricing | `api.agentphone.ai` answers 405 and 401 as expected | No | $5 sign-up credit covers the first month; $3 a month per number. Its OTP now goes to the agent's own AgentMail inbox from Layer 1. |
| Dial | Non-US numbers, iMessage (Layer 2) | Its skills page: `dial auth login`, `verify-otp`, `register-number`, `wait-for` | `@getdial/cli` 0.44.0 on npm | No | Its sign-up needs an SMS-capable phone that is not a Dial number, described as one the user keeps. Using the agent's AgentPhone number is our inference and is untested. |
| A local wallet (Layer 4) | Holding and spending value, self-custodied | Standard Ethereum/Solana keypair generation, documented by `ethers` and the Solana CLI themselves | `node`, `ethers` (npm) and `solana-keygen` are standard, widely used tools | Key generation only; no funds moved | The private key is the agent's (or the human's, if they hold it instead), not a vendor's. |
| `x402` / `@x402/*` | Paying an x402 service from the local wallet (Layer 4, 9) | The protocol's own README (x402-foundation/x402 on GitHub) | `x402` on PyPI (v2.24.0) and `@x402/core`, `@x402/evm`, `@x402/svm`, `@x402/fetch` on npm (v2.27.0) confirmed present, 2026-09-22 | No payment made | An open, multi-chain protocol maintained by the x402 Foundation, not a single vendor; the client libraries are the documented, current install path (the unscoped `x402-fetch` package also exists but the scoped `@x402/*` packages are what the project's own README now tells people to install). |
| x402 Bazaar | Discovering paid x402 endpoints, no signup | Coinbase's Bazaar docs | `api.cdp.coinbase.com/platform/v2/x402/discovery/resources` returned 200 with 15,141 entries (2026-09-21) | Listing only | The `query` parameter did not filter when tested. No paid call was made. |
| Local TOTP (`scripts/totp.py`) | 2FA codes, Layer 13 | RFC 6238 (TOTP) and RFC 4226 (HOTP), read directly | Standard library only, nothing to reach | Yes: matches all 5 RFC 6238 Appendix B test vectors and all 10 RFC 4226 Appendix D test vectors exactly | No vendor at all; this is the actual algorithm every authenticator app implements. |
| Local QR encoder (`scripts/qr.py`) | QR code on the business-card back | ISO/IEC 18004 Model 2 spec, read directly | Standard library only, nothing to reach | Yes: all 80 version/ECC combinations (versions 1-20, L/M/Q/H) at full capacity decoded correctly via macOS `CIDetector` (CoreImage); 48 payload/mask combinations tested | Pure-Python encoder, no vendor. Only macOS CoreImage was used as the decode reference; no Android or other reader was tested. |
| Local vCard and card renderer (`scripts/vcard.py`, `scripts/card.py`) | Business card outputs: card.vcf, front.png, back.png, card.pdf | RFC 6350 (vCard), read directly; Pillow docs for image and PDF rendering | Standard library plus Pillow; nothing external to reach | Yes: full vCard round-tripped through Contacts.framework (CNContactVCardSerialization) on macOS, including Arabic names and an injection fixture. Card images verified by visual inspection. PDF renders correctly in macOS Preview. | No vendor. vCard was parsed on macOS only; no Windows Contacts or Android import was tested. |
| Local calendar (`scripts/ical.py`) | A private calendar, Layer 15 | RFC 5545 (iCalendar), read directly | Standard library only | Yes: add, list, delete and date-range filtering checked in `tests/test_calendar.py`, plus balanced VEVENT blocks and correct line folding | No account. Cal.com (below) is still used for the optional public booking page. |
| Apify | One token, thousands of scrapers | Its API docs for the synchronous run endpoint | Not called | No | $5 a month free, no card, per its pricing page. |
| OpenRouter | One key, many models | Its public docs and pricing pages | Not called | No | Login options, free models and USDC top-up (5% fee) are from public pages. |
| AgentCard | Agent cards | Its website | `agentcard` 0.3.0 on npm, no README | No | Human identity check per the vendor. Flow unconfirmed. |
| AgentWallet | Agent cards, marketing | Its website | The site loads. `api.agentwallet.ai` has no DNS record (2026-09-21) | No | Do not rely on it until its docs give a working endpoint. |
| Open-Meteo, Nominatim, Wikipedia REST, Jina Reader, DuckDuckGo HTML | Keyless eyes | Their public docs | All returned 200 (2026-09-21) | Read-only GETs | Nominatim needs a real User-Agent and about one request a second. |
| edge-tts, faster-whisper, Playwright | Local voice, transcription, browser | PyPI and npm pages | Present on PyPI and npm | No | edge-tts uses an unofficial endpoint that may change. |
| GitHub | Accounts, tokens, repos | REST docs | The public username check and `git` worked | Yes, for git and the API calls the backup uses | Sign-up needs a person: CAPTCHA and terms. |
| Cal.com, Stripe, Slack, Telegram, Discord, Vercel, Supabase | Account layers | Public docs, token pages | Not exercised | No | Each sign-up may show a CAPTCHA. |

## How to add, update, or remove a row

Read the vendor's docs, run what you can, write what you did and the date, and say plainly what you could not check. If a service turns out to need a person, say so in its layer guide and in the human-needed tables. If a provider is dropped, move its row to **Removed** with the real reason rather than deleting it outright: a decision made once, and not written down, gets relitigated by someone who does not know why it was made.
