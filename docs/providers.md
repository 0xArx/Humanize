# Providers: what was checked

The layers cite real services. This page says how far each citation has been verified, so nobody has to guess. Dates are when the check was made.

**Levels**

- **Read:** the vendor's own documentation or source was read and the endpoint, package or command matches.
- **Reachable:** the host or package answered (an HTTP status, or `npm view`, or PyPI).
- **Exercised:** we ran it end to end.

No live sign-up has been exercised. Signing up creates a real account, so that is left for a real run.

| Provider | Used for | Read | Reachable | Exercised | Notes |
|----------|----------|------|-----------|-----------|-------|
| Mailgent | Inbox, DID, vault, calendar, wallet, x402 | CLI README and source (vault, calendar, payments); sign-up curl from the vendor site | `api.mailgent.dev` answers 401 to an unauthenticated GET; `@mailgent-dev/cli` 0.7.1 on npm; MCP endpoint answers 401 | No | The sign-up response field names are not in the CLI. The `--data` field for a `TOTP` entry is undocumented. The CLI's README omits calendar, but the source has it. |
| AgentMail | Recognisable address | `POST /v0/agent/sign-up` and `/v0/agent/verify` pages, with request and response fields | `agentmail` on npm 0.5.27 and PyPI | No | Whether it accepts a `mailgent.dev` address as the human email is untested. Unverified accounts can only email that address. Sign-up is idempotent and rotates the key. |
| AgentPhone | Number, SMS, voice | Its skills page: sign-up, verify, calls, messages, voices, verify endpoints and pricing | `api.agentphone.ai` answers 405 and 401 as expected | No | $5 sign-up credit covers the first month; $3 a month per number. |
| Dial | Non-US numbers, iMessage | Its skills page: `dial auth login`, `verify-otp`, `register-number`, `wait-for` | `@getdial/cli` 0.44.0 on npm | No | Its sign-up needs an SMS-capable phone that is not a Dial number, described as one the user keeps. Using the agent's AgentPhone number is our inference and is untested. |
| x402 and the Bazaar | Pay per call from the wallet, no signup | Coinbase's Bazaar docs | `api.cdp.coinbase.com/platform/v2/x402/discovery/resources` returned 200 with 15,141 entries (2026-09-21) | Listing only | The `query` parameter did not filter when tested. No paid call was made. |
| Apify | One token, thousands of scrapers | Its API docs for the synchronous run endpoint | Not called | No | $5 a month free, no card, per its pricing page. |
| OpenRouter | One key, many models | Its public docs and pricing pages | Not called | No | Login options, free models and USDC top-up (5% fee) are from public pages. |
| AgentCard | Agent cards | Its website | `agentcard` 0.3.0 on npm, no README | No | Human identity check per the vendor. Flow unconfirmed. |
| AgentWallet | Agent cards, marketing | Its website | The site loads. `api.agentwallet.ai` has no DNS record (2026-09-21) | No | Do not rely on it until its docs give a working endpoint. |
| Open-Meteo, Nominatim, Wikipedia REST, Jina Reader, DuckDuckGo HTML | Keyless eyes | Their public docs | All returned 200 (2026-09-21) | Read-only GETs | Nominatim needs a real User-Agent and about one request a second. |
| edge-tts, faster-whisper, Playwright | Local voice, transcription, browser | PyPI and npm pages | Present on PyPI and npm | No | edge-tts uses an unofficial endpoint that may change. |
| GitHub | Accounts, tokens, repos | REST docs | The public username check and `git` worked | Yes, for git and the API calls the backup uses | Sign-up needs a person: CAPTCHA and terms. |
| Cal.com, Stripe, Slack, Telegram, Discord, Vercel, Supabase | Account layers | Public docs, token pages | Not exercised | No | Each sign-up may show a CAPTCHA. |

## How to add or update a row

Read the vendor's docs, run what you can, write what you did and the date, and say plainly what you could not check. If a service turns out to need a person, say so in its layer guide and in the human-needed tables.
