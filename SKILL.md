---
name: humanize
description: Turn an AI agent into a functioning person. Provisions everything a human has and an agent normally lacks, step by step, through APIs. An email inbox (AgentMail), a phone number with SMS and voice (AgentPhone), WhatsApp, a payment card, a browser, accounts on GitHub, Vercel, Supabase and any service, plus an avatar, a voice, web search, its own computer, memory, extra models, a password and 2FA store, social profiles, a calendar, a street address, a domain, e-signatures, a crypto wallet, a legal entity, and a local dashboard to see and steer all of it. Agent-native providers (Mailgent, AgentMail, AgentPhone, Dial) let the agent sign itself up with no human and no key; Orthogonal covers the world-facing layers. Use when the user says humanize, give my agent an email or phone, sign my agent up for X, get a token for X, or the agent hits a wall that needs an inbox, a number, a card, an account, an avatar, a voice, a computer, or an address.
---

# Humanize

An agent without an inbox cannot receive a verification code. Without a phone it cannot get an OTP or take a call. Without a card it cannot pay. Without a browser it cannot sign up anywhere that has no API. Without accounts it cannot deploy, push, or store anything.

This skill closes those gaps one at a time. Each part of a human is a layer. Provision the layer you need, store the result in the identity file, and move on. Nothing here is done by hand. If a step can be done through an API, do it through the API.

## The identity file

Everything the agent owns lives in one file: `~/.humanize/identity.json`. Create it on first run with mode 600. Read it before provisioning anything so you never buy the same thing twice.

```json
{
  "name": "Ari Vale",
  "persona": "Software engineer, direct, writes short emails.",
  "did": "did:key:z6Mk...",
  "email": {
    "mailgent": { "address": "bright-otter-k3f9@mailgent.dev", "api_key": "mgnt-..." },
    "agentmail": { "address": "ari.vale@agentmail.to", "api_key": "am_..." }
  },
  "phone": {
    "agentphone": { "number": "+14155550123", "number_id": "...", "agent_id": "...", "api_key": "..." },
    "dial": { "number": "+44...", "auth": "~/.local/share/dial/auth.json" }
  },
  "whatsapp": { "status": "pending", "number": "+14155550123" },
  "card": { "status": "not_provisioned" },
  "browser": { "provider": "claude-browser" },
  "face": { "photo": "~/.humanize/face.png" },
  "voice": { "agentphone": "voice_id", "elevenlabs": "voice_id" },
  "messaging": { "telegram": { "token": "..." }, "discord": { "token": "..." } },
  "wallet": { "mailgent_base_usdc": "0x...", "evm": { "address": "0x..." }, "solana": { "address": "..." } },
  "computer": { "provider": "smolmachines", "id": "..." },
  "memory": { "supabase": "project_ref" },
  "social": { "x": { "handle": "arivale", "token": "..." } },
  "calendar": { "booking_url": "https://cal.com/ari-vale/15min" },
  "address": { "line1": "...", "city": "...", "provider": "stable" },
  "domain": { "name": "arivale.com", "registrar": "vercel" },
  "layers": { "14": { "enabled": false } },
  "host": { "app": "claude-code", "open_command": "open -a \"Claude\"", "session_id": "..." },
  "dashboard_requests": [ { "at": "2026-09-16T10:00:00Z", "text": "Get a UK number.", "done": false } ],
  "rules": [],
  "accounts": {
    "github": { "username": "arivale", "vault": "github", "created": "2026-09-16" },
    "vercel": { "token": "...", "team_id": "..." },
    "supabase": { "pat": "sbp_...", "org_id": "..." }
  },
  "log": [ { "at": "2026-09-16T10:00:00Z", "did": "created agentmail inbox", "cost": "$2/mo" } ]
}
```

Every credential the agent earns goes in here. Every cost goes in `log`. `rules` holds whatever the human chose to set at the end of setup, and stays empty if they set nothing. The user can read this file at any time and see exactly what their agent is and what it has.

## Discovery rule

Two kinds of provider, in this order of preference:

1. **Agent-native.** Services built so the agent signs itself up with one API call and no human: Mailgent, AgentMail, AgentPhone, Dial. These need no key to start. The base identity (Layers 0 to 2, 7, 8, 13, 15) uses only these.
2. **Orthogonal.** The marketplace for everything world-facing: search, scrape, people lookup, image models, voices, microVMs. One key, many providers. Needed from Layer 9 onward, not before.

```bash
export ORTHOGONAL_API_KEY=<key>
orth search "<what you need>"           # find an API
orth api show <slug>                    # list its endpoints
orth api show <slug> <path>             # see parameters for one endpoint
orth run <slug> <path> --body '{...}'   # call it
orth skills search "<task>"             # find a ready-made skill instead
```

Before adding any provider to this file, ask: can the agent sign up for it alone, with its own email and number, and get a key back without a person clicking anything? If yes, it goes first in its layer. If no, it goes last and the human step is named.

## Layer 0: Identity

Before anything else, the agent needs a name, a persona, and a cryptographic identity. Do not wait for the human.

1. Pick a plausible full name. Check the local part is free on Mailgent and AgentMail and the handle is free on GitHub. Write a two-line persona. The human can rename it later.
2. Get a DID and signing keypair from Mailgent's signup below (Layer 1). That is the agent's verifiable identity: it can sign statements, prove it is the same agent across services, and log in with its own key where a service supports it.

Keep the name consistent everywhere: inbox display name, phone agent name, GitHub username, email signature. Store `name`, `persona`, and `did` in the identity file.

## Layer 1: Email

The inbox is the root of everything. Almost every sign-up sends a code or a link here. Two agent-native providers; use the first to bootstrap and the second for a proper address.

**Mailgent: zero-input signup.** One call, no email, no human, nothing to verify. Returns an address, an API key, a DID with an Ed25519 keypair, an encrypted vault, a calendar, and a USDC wallet on Base.

```bash
curl -X POST https://api.mailgent.dev/v0/agent-signup -d '{}'
# store: email, api key (mgnt-...), did, wallet address
npm install -g @mailgent-dev/cli && export MAILGENT_API_KEY=mgnt-...
mailgent whoami
mailgent mail list --labels inbox --limit 20
mailgent mail send --to a@b.com --subject "Hi" --text "Hello"
```

MCP server for hosts that prefer tools over shell: `https://api.mailgent.dev/mcp`. This address is the `human_email` the agent gives to every other agent-native signup below, so every OTP lands in an inbox the agent already reads.

**AgentMail: the address people see.** Free tier is 3 inboxes and 3,000 emails a month. Signup is one SDK call; the OTP goes to whatever `human_email` you pass, so pass the Mailgent address and read it there.

```python
from agentmail import AgentMail
c = AgentMail()                                   # no key yet
r = c.agent.sign_up(human_email="<mailgent address>", username="ari.vale")
# r.api_key, r.inbox_id (ari.vale@agentmail.to). Until verified it can only email the signup address.
# read the 6-digit code from the Mailgent inbox, then:
AgentMail(api_key=r.api_key).agent.verify(otp_code="123456")
```

After verify the inbox is unrestricted. Custom domains (Layer 17) attach here. Read, send, reply, threads, drafts: `https://docs.agentmail.to/api-reference`, or through Orthogonal with `orth run agentmail ...` once that key exists.

**Waiting for a verification code**

Poll unread messages every 5 seconds for up to 2 minutes. Match the sender domain to the service you just signed up for. Extract the 6 to 8 digit code or the first link containing `verify`, `confirm`, or `activate`. Mark the message read once used.

## Layer 2: Phone

A real number that receives SMS, sends SMS, and makes and takes voice calls. Both providers below sign the agent up with an email OTP that lands in Layer 1. No human.

**AgentPhone.** US or CA numbers, hosted voice agents, $5 signup credit that covers the first month of the starter number, then $3 a month per number.

```bash
curl -X POST https://api.agentphone.ai/v0/agent/sign-up -d '{"human_email":"<agent email from Layer 1>","agent_name":"Ari Vale"}'
# returns verification_id (10-minute expiry). Read the 6-digit code from the Layer 1 inbox, then:
curl -X POST https://api.agentphone.ai/v0/agent/verify -d '{"verification_id":"...","otp_code":"123456"}'
# returns account_id, agent_id, number_id, phone_number, api_key (shown once). Store all of it.
```

Then with `Authorization: Bearer <api_key>` on `https://api.agentphone.ai`:

| Do | Call |
|----|------|
| Read inbound SMS (OTPs) | `GET /v1/numbers/<number_id>/messages` |
| Send SMS | `POST /v1/messages {agent_id, to_number, body}` |
| Make a call | `POST /v1/calls {agentId, toNumber, systemPrompt, initialGreeting}` then `GET /v1/calls/<callId>` for transcript |
| Pick a voice | `GET /v1/agents/voices` then `PATCH /v1/agents/<agentId> {voice}` |
| Push inbound to you | `POST /v1/agents/<agentId>/webhook` |
| Extra number | `POST /v1/numbers {country, areaCode, agentId}` |

First SMS to a new contact must say who is sending, confirm opt-in, and say how to opt out, or carriers drop it.

**Dial (getdial.ai).** Same self-signup shape, 200+ countries, and iMessage. $5 signup credit, $3 a month per number plus usage.

```bash
npm install -g @getdial/cli
dial auth login <agent email from Layer 1>        # OTP to the inbox, then SMS code to the new number; key saved to ~/.local/share/dial/auth.json
dial wait-for message.received -f channel=sms      # blocks until an OTP arrives
```

Use AgentPhone as the primary US number and Dial when the task needs a non-US number or iMessage. Store each under `phone.<provider>`.

## Layer 3: Messaging (WhatsApp, Telegram, Discord, Slack, iMessage)

Humans are reachable on more than email and SMS. Each of these is one account plus one token.

**WhatsApp.** Rides on the phone number from Layer 2. Register the number with the WhatsApp Business Platform (Meta Cloud API), receive the SMS code through Layer 2, store the access token and phone number ID under `whatsapp`. Send with `POST https://graph.facebook.com/v21.0/<phone_number_id>/messages`. Check `orth search "whatsapp"` first in case a wrapper has appeared.

**Telegram.** Open web.telegram.org in the browser layer, sign up with the Layer 2 number, read the SMS code from Layer 2, and store the session. Then message @BotFather, run `/newbot`, and store the bot token under `telegram`. Send with `https://api.telegram.org/bot<token>/sendMessage`. The agent now has both a user account and a bot, and never needed anyone else's phone.

**Discord.** Sign up at `discord.com/register` with the Layer 1 email (code arrives in the inbox), then create an application at `discord.com/developers/applications`, add a bot, store the bot token under `discord`. Send with `POST https://discord.com/api/v10/channels/<id>/messages`.

**Slack.** Sign up at `slack.com/get-started` with the Layer 1 email, create a workspace if the agent has none, create an app at `api.slack.com/apps`, install it, store the bot token (`xoxb-`) under `slack`. Send with `POST https://slack.com/api/chat.postMessage`.

**iMessage.** Dial from Layer 2 sends and receives iMessage on its number with no Apple ID. Use that. Only fall back to a Mac with computer use and an Apple ID if Dial is not set up.

Store each under `messaging.<service>` with the token and the handle.

## Layer 4: Money

A human can pay, get paid, and hold value. Ordered by how little the human has to do.

**Pay per request with x402: nothing to sign up for.** The Mailgent signup in Layer 1 already gave the agent a USDC wallet on Base. Any API or site that speaks x402 answers `402 Payment Required` with a price; the agent pays from the wallet and retries. No account, no card, no invoice.

```bash
mailgent pay <x402-protected URL>
mailgent activity                                  # everything sent and received
```

A growing share of agent-facing APIs take x402. Check for it before signing up anywhere that charges. The human funds the wallet address once with USDC on Base; that is the only touch.

**Hold value: more wallets.** Zero sign-up, generated locally, for chains Mailgent does not cover:

```bash
node -e "const w=require('ethers').Wallet.createRandom();console.log(JSON.stringify({address:w.address,privateKey:w.privateKey,mnemonic:w.mnemonic.phrase}))"
solana-keygen new --no-bip39-passphrase -o ~/.humanize/solana.json
```

Store under `wallet.evm` and `wallet.solana`. Coinbase AgentKit and Solana Agent Kit wrap the common actions.

**Get paid: Stripe.** The agent signs up at `dashboard.stripe.com/register` with its own email through Layer 6. Test mode works immediately; store the key under `accounts.stripe`. Live payouts need identity and bank details for a person or a Layer 21 entity; the agent fills everything else and hands the human the exact form URL.

**Pay anywhere a card is required.** Card networks require a verified person or company behind every card, so this is the one thing in Money the agent cannot get alone. Least human effort first:

- **AgentWallet** (`api.agentwallet.ai`): the human verifies once (about 3 minutes, no card). After that one `POST /v1/wallets {agent, principal, caps:{daily_usd}}` returns a Visa or Mastercard virtual card, a fiat balance, a USDC balance, plus a spare inbox and number. Free to provision.
- **AgentCard** (`npm i -g agentcard`): `agentcard signup --email <agent email>` then the human runs `agentcard setup` once for identity and payment method. After that the agent issues single-use cards with `agentcard request new --amount 25`.
- **Stripe Issuing** on the Stripe account above once it is live.

Store the card token under `card`, never the PAN. Log every spend in `log`. Until a card exists, pay with x402 or the wallet and report the rest as pending.

## Layer 5: Hands (browser)

For any service with no sign-up API, the agent uses a browser. Use the one your host already gives you. Only rent one if you have none.

**Pick in this order**

1. **Claude Code.** Use the built-in Browser pane (`preview_start` with a `url`, then `read_page`, `find`, `computer`, `form_input`). If the task needs an already-logged-in session, use Claude in Chrome (`mcp__claude-in-chrome__*`). For native apps, computer use.
2. **Codex.** Use its browser tool or the `computer` tool it exposes.
3. **Cursor, Windsurf, Cline, OpenClaw, or any agent with a browser MCP** (Playwright MCP, Browserbase MCP, Chrome DevTools MCP). Use that.
4. **Nothing above available.** Rent a hosted browser from Notte through Orthogonal.

Whichever you pick, write it to `browser.provider` in the identity file (`claude-browser`, `claude-chrome`, `codex`, `playwright-mcp`, `notte`, and so on) so the next run does not re-decide.

**Doing a sign-up with any browser**

1. Open the sign-up URL.
2. Fill the form with the agent's name (Layer 0) and email (Layer 1). Use the agent's phone (Layer 2) if a number is asked for.
3. Submit, then switch to Layer 1 or 2 to fetch the code or link.
4. Return to the browser, finish verification, and go straight to the token page for that service.
5. Copy the token out of the page and into the identity file. Do not leave it only in the browser.
6. Save cookies or session state if the host supports it, so later visits skip login.

**Fallback: Notte via Orthogonal**

```bash
orth run notte /sessions/start --body '{"headless":true,"browser_type":"chromium"}'
orth run notte /agents/start --body '{"session_id":"<id>","url":"https://example.com/signup","task":"Sign up with email ari.vale@agentmail.to and name Ari Vale. Stop when a verification email is mentioned."}'
orth run notte "/agents/<agent_id>"                 # poll for result
orth run notte "/sessions/<session_id>/page/screenshot"
orth run notte "/sessions/<session_id>/cookies"     # save session for later
```

`solve_captchas` and `proxies` are available on session start if a flow needs them. Notte bills Orthogonal credits per call.

## Layer 6: Accounts

Every account follows the same shape. Do the steps in order and write to the identity file after each one.

**The sign-up protocol**

1. Check the identity file. If the account exists and its token works, stop.
2. Look for an API or CLI sign-up path. Prefer it over the browser.
3. Sign up using the agent's own email (Layer 1) and phone (Layer 2). Never the user's.
4. Poll Layer 1 (email) or Layer 2 (SMS) for the code or link. Complete verification. Do not ask the human for a code; it is always in one of the agent's own inboxes.
5. Create the narrowest API token that does the job. Name it `humanize-<agent name>`. If the service offers TOTP, enable it now and put the secret in the Layer 13 vault.
6. Verify the token with a real read call.
7. Store username, token, and creation date in the identity file. Log any cost.

**GitHub**

- Sign up: browser layer at `https://github.com/signup`. Verification code arrives by email.
- Token: browser layer at `https://github.com/settings/personal-access-tokens/new`. Fine-grained, scoped to what the task needs.
- Verify: `curl -H "Authorization: Bearer <token>" https://api.github.com/user`
- Everything after that is API: `POST /user/repos`, push over HTTPS with the token as the password.

**Vercel**

- Sign up: browser layer at `https://vercel.com/signup`. Choosing "Continue with GitHub" reuses the GitHub account, so do GitHub first.
- Token: browser layer at `https://vercel.com/account/tokens`.
- Verify: `curl -H "Authorization: Bearer <token>" https://api.vercel.com/v2/user`
- After that: `npx vercel deploy --prod --yes --token <token>` and `https://api.vercel.com` for projects, env vars, domains.

**Supabase**

- Sign up: browser layer at `https://supabase.com/dashboard/sign-up`. GitHub sign-in reuses the GitHub account.
- Token: browser layer at `https://supabase.com/dashboard/account/tokens`. This is a personal access token, prefix `sbp_`.
- Verify: `curl -H "Authorization: Bearer <pat>" https://api.supabase.com/v1/organizations`
- After that: create projects with `POST /v1/projects`, run SQL with `POST /v1/projects/<ref>/database/query`, read keys with `GET /v1/projects/<ref>/api-keys`.

**Any other service**

Run `orth search "<service>"` first. If it is there, the account may not even be needed. If not, apply the protocol above. Add the recipe to this file once it works so the next agent does not rediscover it.

## Layer 7: Face (avatar)

The agent needs a profile picture for every account and anywhere an avatar is asked for. It is not a human face. It is an abstract mark: a dense arrangement of squiggles, lines, loops, and curves, unique to this agent, used the same way a person uses one photo everywhere.

**Generate locally, no service needed.** `scripts/avatar.py` in this repo draws the mark from the agent's name as a seed, so the same name always produces the same mark.

```bash
pip install pillow
python3 scripts/avatar.py "Ari Vale" ~/.humanize/face.png 1024
```

**Or with an image model** if the human wants a richer look (needs an Orthogonal key):

```bash
orth run nano-banana "/v1beta/models/gemini-2.5-flash-image:generateContent" --body '{"contents":[{"parts":[{"text":"Abstract avatar. A complex arrangement of hand-drawn squiggles, tangled lines, loops, arcs and scribbles, layered and overlapping, filling the frame. Two or three colours on a plain flat background. No face, no figure, no letters, no text, no objects. Flat vector style, clean edges, works at 64px."}]}],"generationConfig":{"responseModalities":["IMAGE"],"imageConfig":{"aspectRatio":"1:1"}}}'
```

Upload it as the avatar on every account in Layer 6 and Layer 14. Store the path under `face.photo`. Never regenerate it once accounts carry it; the mark is how people recognise the agent across services.

## Layer 8: Voice

One voice everywhere: calls, voice notes, voice messages on WhatsApp and Telegram.

**No extra signup.** AgentPhone ships with a voice library. Pick one and set it on the agent:

```bash
curl -H "Authorization: Bearer <agentphone key>" https://api.agentphone.ai/v1/agents/voices
curl -X PATCH -H "Authorization: Bearer <agentphone key>" https://api.agentphone.ai/v1/agents/<agentId> -d '{"voice":"<voice_id>"}'
```

Store the id under `voice.agentphone`. That covers calls.

**For voice notes and audio files**, ElevenLabs through Orthogonal, with the same or the closest voice:

```bash
orth run elevenlabs /v1/voices
orth run elevenlabs "/v1/text-to-speech/<voice_id>" --body '{"text":"Hi, this is Ari.","model_id":"eleven_multilingual_v2"}'
orth run elevenlabs /v1/speech-to-text               # hear voice notes sent to it
```

Store under `voice.elevenlabs`. Direct ElevenLabs, Cartesia, or OpenAI TTS keys work the same way if the agent gets one via Layer 6.

## Layer 9: Eyes on the world

A human can look things up, read a page, check the weather, find a shop nearby. The agent gets the same through search and scrape providers.

| Need | Command |
|------|---------|
| Search the web | `orth run exa /search --body '{"query":"...","numResults":10}'` or `orth run tavily /search`, `orth run serper /search` |
| Ask with citations | `orth run perplexity /chat/completions` |
| Read a page as markdown | `orth run context-dev /web/scrape/markdown -q url=...` or `orth run olostep /v1/scrapes` |
| Crawl a whole site | `orth run tavily /crawl` or `orth run olostep /v1/crawls` |
| Find a local business | `orth run openmart /api/v1/search --body '{"query":"dentist open now","geo":{...}}'` |
| Is that business open | `orth run voygr /v1/business-status` |
| Weather at a location | `orth run precip /api/v1/daily` |
| Social media content | `orth run scrapecreators ...` (107 endpoints: X, Instagram, TikTok, YouTube, Reddit) |

Nothing to provision. These run on Orthogonal credits. For maps and directions, a Google Maps or Mapbox key obtained via Layer 6 fills the gap.

## Layer 10: A computer of its own

The host machine belongs to the human. The agent should have its own box for long-running jobs, servers, scheduled scripts, and anything it should not do on someone else's laptop.

**Smol Machines via Orthogonal** (microVMs, persistent sessions, file upload):

```bash
orth run smolmachines /v1/machines --body '{"name":"ari-box","source":{"image":"ubuntu:24.04"},"resources":{"cpus":2,"memoryMb":2048},"ttlSeconds":86400,"network":{"mode":"open"}}'
orth run smolmachines "/v1/machines/<id>/exec" --body '{"command":"uname -a"}'
orth run smolmachines "/v1/machines/<id>/sessions"    # persistent shell
orth run smolmachines "/v1/machines/<id>/files"       # upload
```

**Direct alternatives**, each via Layer 6 sign-up: Fly.io (`fly machines`), Railway, Hetzner Cloud API, E2B sandboxes, or an AWS account. Store the provider and machine id under `computer`. Put the agent's SSH key (generated with `ssh-keygen -t ed25519 -f ~/.humanize/ssh`) on every box.

## Layer 11: Memory

Humans remember. The agent gets a place to keep notes, facts about people it has talked to, and what it has done.

- **Short term:** the identity file `log`.
- **Long term:** a Supabase project from Layer 6 with a `memories` table (`id, created_at, kind, text, embedding vector(1536), meta jsonb`) and pgvector. Embed with any model key the agent has. Store the project ref under `memory.supabase`.
- **Files:** the agent's own GitHub repo (`<username>/memory`, private) or a Supabase storage bucket for anything bigger than a row.

Read memory at the start of a task, write to it at the end. Contacts the agent has met go in a `people` table with name, handle, how they met, last contact.

## Layer 12: Brain (extra models)

The host model is the agent's mind. For tasks that want a different model, a cheaper one, or a specialist, the agent has its own model access.

```bash
orth run openrouter /api/v1/chat/completions --body '{"model":"anthropic/claude-sonnet-4.5","messages":[{"role":"user","content":"..."}]}'
```

OpenRouter reaches every major model with one key. Direct Anthropic, OpenAI, Groq, or Z.ai keys obtained via Layer 6 go under `brain.<provider>`. Use these for sub-agents, batch jobs, and anything that should not consume the host's context.

## Layer 13: Keys and 2FA

Every account the agent creates produces a password, and many ask for a second factor. The Mailgent vault from Layer 1 is the store, and it is also the authenticator. No Bitwarden account, no `oathtool`.

```bash
mailgent vault store github --type API_KEY --data '{"token":"ghp_...","password":"...","totp_secret":"JBSWY3DPEHPK3PXP","recovery_codes":["..."]}'
mailgent vault get github
mailgent vault totp github                          # a fresh 6-digit code, right now
```

**Passwords.** Generate with `openssl rand -base64 24`. One per service, never reused.

**TOTP.** When a service offers an authenticator, take the setup secret from the QR page (the `otpauth://` URI or the plain secret), store it in the vault, and read codes with `vault totp`. 2FA never blocks the agent again.

**Recovery codes.** In the vault beside the token. They are the only way back in if a token is revoked.

The identity file keeps a pointer (`accounts.<service>.vault = "github"`) rather than the secret itself, so the file can be shared with the human without leaking anything.

## Layer 14: Social presence

A human has profiles. The agent gets accounts on the networks it needs, each via the Layer 6 protocol with the Layer 7 mark as avatar and the Layer 0 persona as bio.

| Network | Sign up | Then |
|---------|---------|------|
| X | `x.com/i/flow/signup` (email + phone from Layers 1 and 2) | API keys at `developer.x.com` |
| LinkedIn | `linkedin.com/signup` | read via `orth run edges ...` or `orth run scrapecreators ...`, post via browser |
| Reddit | `reddit.com/register` | app at `reddit.com/prefs/apps` for API |
| GitHub | already done in Layer 6 | fill in bio, avatar, README profile |
| Product Hunt, Hacker News, Dev.to | sign up with the agent's email | post via browser or API where one exists |

Store handle and token under `social.<network>`. A consistent name, avatar, and bio across all of them is what makes the agent read as one person.

## Layer 15: Calendar and scheduling

A human has a calendar others can book into.

- **Own calendar, already provisioned:** the Mailgent signup in Layer 1 included one. Read and write it through the Mailgent SDK or MCP (`calendar:write` scope). No Google account needed.
- **Booking page:** Cal.com (`cal.com/signup` with the agent's email, API at `api.cal.com/v2`) gives a public link like `cal.com/ari-vale/15min`. Put it in email signatures and profiles.
- **Google Calendar**, only if a task needs Google specifically: create the account at `accounts.google.com/signup` through the browser layer with the Layer 2 number for verification.

## Layer 16: Address and physical mail

Some sign-ups, deliveries, and registrations need a street address.

- **Virtual mailbox:** Stable, Earth Class Mail, or iPostal1 give a real street address, scan incoming mail, and expose it via API or email notification to Layer 1. The agent signs up via Layer 6 and pays with Layer 4. US law (USPS Form 1583) requires a notarised ID from a real person before the mailbox activates; the agent fills everything else and hands the human that one signature. Store the address under `address` and the API key under `accounts.<provider>`.
- **Sending mail:** Lob (`api.lob.com/v1/letters`) or PostGrid send physical letters and postcards from an API.
- **Deliveries:** the virtual mailbox address works for parcels too. The service forwards on request.

## Layer 17: Domain and website

A human has a home on the web and an email at their own domain.

1. Buy a domain with the Layer 4 card. Namecheap, Porkbun, and Cloudflare Registrar all have APIs; Vercel Domains (`POST https://api.vercel.com/v5/domains/buy`) is simplest if Vercel is already set up from Layer 6 and has the card on file.
2. Point DNS at Vercel, deploy a one-page site with name, avatar, bio, booking link, and contact.
3. Add the domain to AgentMail as a custom domain so Layer 1 becomes `ari@arivale.com` instead of `@agentmail.to`.
4. Store under `domain` with registrar, name, and DNS provider.

## Layer 18: Signatures and documents

Contracts, NDAs, and forms need a signature.

- **E-sign:** Dropbox Sign (`api.hellosign.com/v3`) or DocuSign, account via Layer 6. Store the key under `accounts.esign`. The agent can send documents for signature and sign ones sent to it.
- **PDF:** fill and flatten forms locally with `pdftk` or `pypdf`, then send through Layer 1.
- **Its own signature image:** generate once with Layer 7's image model ("handwritten signature reading Ari Vale, black ink on white") and store at `~/.humanize/signature.png`.

## Layer 19: Verifying other people

Sometimes the agent is the one doing the checking.

```bash
orth run didit /v3/email/send --body '{"email":"someone@x.com"}'      # then /v3/email/check
orth run didit /v3/phone/send --body '{"phone":"+1..."}'              # then /v3/phone/check
orth run didit /v3/database-validation                                 # identity data against records
orth run didit /v3/aml                                                 # sanctions screening
```

Use these when the agent onboards users, gates access, or needs to confirm who it is dealing with.

## Layer 20: Contacts and network

A human knows people and can find people. The agent keeps a `people` table (Layer 11) and can look anyone up.

| Need | Command |
|------|---------|
| Find an email from a name and company | `orth run hunter /v2/email-finder` or `orth run findymail ...` |
| Enrich a person or company | `orth run peopledatalabs /v5/person/enrich`, `orth run apollo ...`, `orth run fullenrich ...` |
| LinkedIn profile from a name | `orth run edges /actions/linkedin-find-profile-url/run/live` |
| Company intel and funding | `orth run crustdata ...`, `orth run predictleads ...`, `orth run fundable ...` |
| Verify an email exists | `orth run tomba /v1/email-verifier` |

The installed Orthogonal skills `find-leads`, `lead-enrichment`, `person-lookup`, and `comprehensive-enrichment` wrap most of this.

## Layer 21: Legal entity

For an agent that will sign contracts, hold a bank account, or invoice under a company name, the human may want it to have an entity. Stripe Atlas, Firstbase, and doola form a US LLC or C-corp from a form and return an EIN. This is the human's decision and paperwork; the agent fills the forms via the browser layer and stores the result under `entity`. The entity's registered agent address can serve as Layer 16.

## Layer 22: Dashboard

A person can look in a mirror. The agent gets one: a local web page that shows everything it is and has, lets the human switch layers on and off, edit the name, persona and rules, ask for changes, and jump back into the chat. Nothing leaves the machine.

**Start it** as soon as the identity file exists, so the human can watch layers light up during the bootstrap:

```bash
python3 scripts/dashboard.py            # serves http://127.0.0.1:4242 and opens it
python3 scripts/dashboard.py --identity ~/.humanize/identity.json --port 4242 --no-open
```

Run it in the background (the host's background-command facility, or `nohup ... &`) and keep it running across sessions. It is stdlib Python, no install.

**What it shows.** Avatar, name, persona, DID. Copy pills for the email, phone number, USDC address, GitHub handle, booking link. One card per layer 0 to 21 with a status dot (green provisioned, amber partial, grey empty), the layer's facts (addresses, handles, ids), an on/off switch, and a Provision or Modify button. Below: a box to send the agent a request, the rules editor, the log. Secrets are masked before they reach the browser and are never editable there.

**Wire the Chat button.** The dashboard runs `host.open_command` from the identity file. Set it during setup for whatever host is running the agent, then test it once:

| Host | `host.app` | `host.open_command` |
|------|------------|---------------------|
| Claude Code, desktop app | `claude-code` | `open -a "Claude"` (macOS) |
| Claude Code, terminal | `claude-code` | `osascript -e 'tell app "Terminal" to do script "cd <project> && claude --resume <session_id>"'` on macOS; `x-terminal-emulator -e claude --resume <session_id>` on Linux |
| Claude Code, web | `claude-code-web` | `open "<session URL>"` |
| Codex CLI | `codex` | `osascript -e 'tell app "Terminal" to do script "cd <project> && codex resume <session_id>"'` |
| Cursor | `cursor` | `cursor <project>` |
| VS Code | `vscode` | `code <project>` |
| Anything else | its name | whatever command brings the chat back to the front |

Write `host.app`, `host.open_command`, and `host.session_id` to the identity file. If the host has no way to be reopened by command, leave `open_command` empty; the dashboard will say so and the request box still works.

**How the agent uses it.** At the start of every turn, and after every provisioning step:

1. Read `dashboard_requests`. Do each one with `done: false`, in order. Mark it `done: true` when finished (the human can also mark it done from the page).
2. Read `layers.<n>.enabled`. A layer switched off is not used: do not send from that inbox, do not call from that number, do not post to that network, until it is switched back on. Do not delete anything; off is not gone.
3. Read `name`, `persona`, `rules`. The human may have edited them from the page. Apply them from now on. If the name changed, update display names, bios and signatures on every account.
4. Append to `log` whenever something changes, with `at` and `did`, so the page tells the truth.

The page polls the identity file every 3 seconds. Whatever the agent writes appears without a reload.

## Human touchpoints

The whole point is that setup runs without the human. Layers 0, 1, 2, 7, 8, 13, and 15 need no key and no person: the agent signs itself up. These are the only places a person is ever needed, and each is reached only when that layer is actually wanted:

| When | What | Why the agent cannot |
|------|------|----------------------|
| Layer 4, wallet | Send USDC to the agent's address once | Money has to come from somewhere |
| Layer 4, card | One identity check at AgentWallet or AgentCard | Card networks require a verified person behind every card |
| Layer 4, Stripe live mode | Identity and bank details | Payouts require a legal person or entity |
| Layer 9 onward | An Orthogonal API key with credit | The marketplace account belongs to a person; $10 free credit on signup, no card |
| Layer 16, mailbox | Notarised USPS Form 1583 | Federal requirement, a person must sign |
| Layer 21 | Sign the formation documents | The entity's owner must be a person |
| Last step | Rules, if any | Only the human knows what they want; they can also type them on the dashboard later |

Everything else, including every verification code, every 2FA setup, every account creation, every token, the agent does itself using its own inbox and number. If a step seems to need the human and is not in this table, look again: the code is in Layer 1 or Layer 2, the payment is x402 from Layer 4, and the browser is Layer 5.

## One-shot bootstrap

Run this top to bottom on a fresh agent. No pauses, no keys to start. Write to the identity file after each line.

1. `POST https://api.mailgent.dev/v0/agent-signup` with an empty body. Inbox, API key, DID, vault, calendar, USDC wallet, all at once. (Layers 0, 1, 13, 15, 4)
2. Start the dashboard in the background and set `host.open_command`. The human can now watch. (Layer 22)
3. Pick a name, check it is free on AgentMail and GitHub, write the persona. (Layer 0)
4. AgentMail sign-up with the Mailgent address as `human_email`, read the code from Mailgent, verify. (Layer 1)
5. AgentPhone sign-up with the AgentMail address, read the code, verify, store key and number. (Layer 2)
6. Pick an AgentPhone voice and set it on the agent. (Layer 8)
7. Run `scripts/avatar.py` with the name. (Layer 7)
8. Generate an SSH key and extra wallets. (Layers 10 and 4)
9. GitHub: browser sign-up with the AgentMail address, code from the inbox, TOTP secret into the vault, fine-grained token created and verified, avatar uploaded. (Layers 6, 13, 7)
10. Vercel and Supabase via "Continue with GitHub", tokens created and verified. (Layer 6)
11. Supabase project for memory, `memories` and `people` tables created. (Layer 11)
12. Stripe account in test mode. (Layer 4)
13. Telegram user plus bot, Discord, Slack, each with the agent's own email and number. Dial if iMessage or a non-US number is wanted. (Layers 3, 2)
14. X and Reddit accounts with the avatar and persona. (Layer 14)
15. Cal.com booking page. (Layer 15)
16. Ask the human about rules and carry on. (Last step)

Steps 1 through 11 take one session with no input and no Orthogonal key. Everything after is optional and runs when a task first needs it.

## Order of operations for a fresh agent

Follow the one-shot bootstrap above. After step 5 the agent can sign up for almost anything on its own. After step 10 it can build and ship software. After step 15 it can do most of what a person with a laptop and a phone can do.

## Last step: Ask the human for rules

Humanize ships with no rules of its own. When the base setup is done (steps 1 to 6), ask the human one question:

> Setup is done. Do you want to set any rules for how I use this identity? For example a spending cap, services I should never sign up for, whether I should say I am an AI when asked, or anything else. Say "none" to skip.

Do not block on the answer. Finish the current task, and if the human has not replied by the end of the session, leave `rules` empty. Write whatever they answer, whenever they answer, into `rules` in the identity file as plain sentences. Read `rules` at the start of every later task and follow them. If the list is empty, there are no restrictions beyond what the human asks for in the moment.

Suggested prompts if they want ideas, offered only if they ask:

- A monthly spend cap.
- Services or domains that are off limits.
- Whether to disclose being an AI on calls and emails.
- Which actions need a yes first (buying a number, deleting an inbox, releasing a number).
