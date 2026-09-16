---
name: humanize
description: Turn an AI agent into a functioning person. Provisions everything a human has and an agent normally lacks, step by step, through APIs. An email inbox (AgentMail), a phone number with SMS and voice (AgentPhone), WhatsApp, a payment card, a browser, accounts on GitHub, Vercel, Supabase and any service, plus an avatar, a voice, web search, its own computer, memory, extra models, a password and 2FA store, social profiles, a calendar, a street address, a domain, e-signatures, a crypto wallet, and a legal entity. Uses Orthogonal where it has a provider and goes direct to vendors everywhere else. Use when the user says humanize, give my agent an email or phone, sign my agent up for X, get a token for X, or the agent hits a wall that needs an inbox, a number, a card, an account, an avatar, a voice, a computer, or an address.
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
  "email": { "provider": "agentmail", "address": "ari.vale@agentmail.to", "inbox_id": "ari.vale@agentmail.to" },
  "phone": { "provider": "agentphone", "number": "+14155550123", "number_id": "...", "agent_id": "...", "api_key": "..." },
  "whatsapp": { "status": "pending", "number": "+14155550123" },
  "card": { "status": "not_provisioned" },
  "browser": { "provider": "claude-browser" },
  "face": { "photo": "~/.humanize/face.png" },
  "voice": { "elevenlabs": "voice_id" },
  "messaging": { "telegram": { "token": "..." }, "discord": { "token": "..." } },
  "wallet": { "evm": { "address": "0x..." }, "solana": { "address": "..." } },
  "computer": { "provider": "smolmachines", "id": "..." },
  "memory": { "supabase": "project_ref" },
  "social": { "x": { "handle": "arivale", "token": "..." } },
  "calendar": { "booking_url": "https://cal.com/ari-vale/15min" },
  "address": { "line1": "...", "city": "...", "provider": "stable" },
  "domain": { "name": "arivale.com", "registrar": "vercel" },
  "rules": [],
  "accounts": {
    "github": { "username": "arivale", "token": "ghp_...", "password": "...", "totp_secret": "...", "created": "2026-09-16" },
    "vercel": { "token": "...", "team_id": "..." },
    "supabase": { "pat": "sbp_...", "org_id": "..." }
  },
  "log": [ { "at": "2026-09-16T10:00:00Z", "did": "created agentmail inbox", "cost": "$2/mo" } ]
}
```

Every credential the agent earns goes in here. Every cost goes in `log`. `rules` holds whatever the human chose to set at the end of setup, and stays empty if they set nothing. The user can read this file at any time and see exactly what their agent is and what it has.

## Discovery rule

Before provisioning any capability, search Orthogonal. It is the marketplace this skill is built on, and new providers show up there first.

```bash
export ORTHOGONAL_API_KEY=<key>
orth search "<what you need>"           # find an API
orth api show <slug>                    # list its endpoints
orth api show <slug> <path>             # see parameters for one endpoint
orth run <slug> <path> --body '{...}'   # call it
orth skills search "<task>"             # find a ready-made skill instead
```

If Orthogonal has it, use it through `orth run`. If it does not, go direct: sign up with the vendor through Layer 6 and call their API with the key from the identity file. Nothing in this skill is limited to Orthogonal. If there is no API at all, use the browser layer.

## Layer 0: Identity

Before anything else, the agent needs a name and a persona. Do not wait for the human. Pick a plausible full name that is free as a username on GitHub and as a local part on AgentMail (check both), write a two-line persona, and continue. The human can rename it later. Keep it consistent everywhere: inbox display name, phone agent name, GitHub username, email signature.

Write `name` and `persona` to the identity file. Every later layer reads them.

## Layer 1: Email (AgentMail)

The inbox is the root of everything. Almost every sign-up sends a code or a link here.

**Provision**

```bash
orth run agentmail /v0/inboxes --body '{"username":"ari.vale","display_name":"Ari Vale"}'
```

Cost: $2 per month per inbox. Inboxes idle for 30 days are deleted, so any read resets the timer. Store `inbox_id` (it is the email address itself) in the identity file.

**Read**

```bash
orth run agentmail "/v0/inboxes/<inbox_id>/messages" -q limit=10 -q labels=unread
orth run agentmail "/v0/inboxes/<inbox_id>/messages/<message_id>"
```

**Send**

```bash
orth run agentmail "/v0/inboxes/<inbox_id>/messages/send" --body '{"to":["x@y.com"],"subject":"...","text":"..."}'
```

Reply, reply-all, forward, drafts, and threads are all under the same slug. `orth api show agentmail` lists them.

**Waiting for a verification code**

Poll unread messages every 5 seconds for up to 2 minutes. Match the sender domain to the service you just signed up for. Extract the 6 to 8 digit code or the first link containing `verify`, `confirm`, or `activate`. Mark the message read once used.

## Layer 2: Phone (AgentPhone)

A US or Canadian number that can receive SMS, send SMS, and make and take voice calls.

**First-time account setup.** AgentPhone sends a one-time code to an email address and returns an API key, a starter agent, and a number in one shot. Give it the agent's own inbox from Layer 1, then read the code out of that inbox. No human in the loop.

```bash
orth run agentphone /v0/agent/sign-up --body '{"human_email":"ari.vale@agentmail.to","agent_name":"Ari Vale"}'
# returns verification_id. Poll Layer 1 for the code:
orth run agentmail "/v0/inboxes/ari.vale@agentmail.to/messages" -q labels=unread -q limit=5
# extract the 6-digit code from the AgentPhone message, then:
orth run agentphone /v0/agent/verify --body '{"verification_id":"...","otp_code":"123456"}'
# returns api_key, agent_id, number. Store all three.
```

**Extra numbers**

```bash
orth run agentphone /v1/numbers --body '{"country":"US","areaCode":"415","agentId":"<agent_id>"}'
```

Cost: $3 per month per number.

**Receive SMS**

```bash
orth run agentphone "/v1/numbers/<number_id>/messages"
```

Same polling rule as email. Most OTPs arrive within 30 seconds.

**Send SMS**

```bash
orth run agentphone /v1/messages --body '{"agent_id":"...","to_number":"+1...","body":"..."}'
```

The first message to any new contact must state who is sending, confirm they opted in, and say how to opt out. Carriers drop messages that skip this.

**Make a call**

```bash
orth run agentphone /v1/calls --body '{"agentId":"...","toNumber":"+1...","systemPrompt":"You are Ari calling to confirm a dentist appointment for Tuesday at 3pm.","initialGreeting":"Hi, this is Ari."}'
orth run agentphone "/v1/calls/<callId>"    # poll for transcript
```

Voices come from `GET /v1/agents/voices`. Set a webhook with `POST /v1/agents/<agentId>/webhook` if you want inbound calls and texts pushed to you instead of polled.

## Layer 3: Messaging (WhatsApp, Telegram, Discord, Slack, iMessage)

Humans are reachable on more than email and SMS. Each of these is one account plus one token.

**WhatsApp.** Rides on the phone number from Layer 2. Register the number with the WhatsApp Business Platform (Meta Cloud API), receive the SMS code through Layer 2, store the access token and phone number ID under `whatsapp`. Send with `POST https://graph.facebook.com/v21.0/<phone_number_id>/messages`. Check `orth search "whatsapp"` first in case a wrapper has appeared.

**Telegram.** Open web.telegram.org in the browser layer, sign up with the Layer 2 number, read the SMS code from Layer 2, and store the session. Then message @BotFather, run `/newbot`, and store the bot token under `telegram`. Send with `https://api.telegram.org/bot<token>/sendMessage`. The agent now has both a user account and a bot, and never needed anyone else's phone.

**Discord.** Sign up at `discord.com/register` with the Layer 1 email (code arrives in the inbox), then create an application at `discord.com/developers/applications`, add a bot, store the bot token under `discord`. Send with `POST https://discord.com/api/v10/channels/<id>/messages`.

**Slack.** Sign up at `slack.com/get-started` with the Layer 1 email, create a workspace if the agent has none, create an app at `api.slack.com/apps`, install it, store the bot token (`xoxb-`) under `slack`. Send with `POST https://slack.com/api/chat.postMessage`.

**iMessage.** Only from a Mac the agent controls. If the host is macOS with computer use, create an Apple ID at `account.apple.com` with the Layer 1 email and Layer 2 number (both codes arrive automatically), then sign into Messages with it. Otherwise skip.

Store each under `messaging.<service>` with the token and the handle.

## Layer 4: Money

A human can pay, get paid, and hold value. Do these in the order below: the first needs nobody, the second needs the human once, the third depends on the second.

**Hold value: a crypto wallet.** Zero sign-up. Generate a keypair locally and store it in the identity file:

```bash
# Ethereum and every EVM chain
node -e "const w=require('ethers').Wallet.createRandom();console.log(JSON.stringify({address:w.address,privateKey:w.privateKey,mnemonic:w.mnemonic.phrase}))"
# Solana
solana-keygen new --no-bip39-passphrase -o ~/.humanize/solana.json
```

Store under `wallet.evm` and `wallet.solana`. Read balances and send with any RPC (Alchemy, Helius, public endpoints). Coinbase AgentKit and Solana Agent Kit wrap the common actions. The human funds the address once and the agent can pay anything that takes crypto from then on.

**Get paid: Stripe.** The agent signs up at `dashboard.stripe.com/register` with its own email through Layer 6 and stores the secret key under `accounts.stripe`. Test mode works immediately. Live payouts need identity and bank details for a real person or a Layer 21 entity; that is the one part of this layer the agent hands to the human, and it does so with the exact form URL and nothing else left to do.

**Pay: a card.** No issuer is on Orthogonal yet. Once the Stripe account above is live, `POST /v1/issuing/cards` gives the agent a virtual card with a limit. Lithic (`POST https://api.lithic.com/v1/cards`) is the direct alternative. Store the card token under `card`, never the PAN. Log every spend in `log` with amount and purpose. Until a card exists, the agent pays with the wallet where crypto is accepted and reports the rest as pending.

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
5. Create the narrowest API token that does the job. Name it `humanize-<agent name>`.
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

**Generate once, reuse everywhere.**

```bash
orth run nano-banana "/v1beta/models/gemini-2.5-flash-image:generateContent" --body '{"contents":[{"parts":[{"text":"Abstract avatar. A complex arrangement of hand-drawn squiggles, tangled lines, loops, arcs and scribbles, layered and overlapping, filling the frame. Two or three colours on a plain flat background. No face, no figure, no letters, no text, no objects. Flat vector style, clean edges, works at 64px."}]}],"generationConfig":{"responseModalities":["IMAGE"],"imageConfig":{"aspectRatio":"1:1"}}}'
```

Vary the colours and line density per agent so two agents never share a mark. Decode the base64, save to `~/.humanize/face.png`, and upload it as the avatar on every account in Layer 6 and Layer 14. Store the path under `face.photo`. Never regenerate it once accounts carry it; the mark is how people recognise the agent across services.

## Layer 8: Voice

Layer 2 gives the agent a voice on phone calls. This layer gives it one voice everywhere: calls, voice notes, voice messages on WhatsApp and Telegram.

```bash
orth run elevenlabs /v1/voices                       # pick one, or
orth run elevenlabs /v1/shared-voices                # browse the library
orth run elevenlabs "/v1/text-to-speech/<voice_id>" --body '{"text":"Hi, this is Ari.","model_id":"eleven_multilingual_v2"}'
orth run elevenlabs /v1/speech-to-text               # hear voice notes sent to it
```

Pick one `voice_id`, store it under `voice.elevenlabs`, and set the same voice on the AgentPhone agent (`PATCH /v1/agents/<agentId>` with `voice`) so the phone and the voice notes match. Direct ElevenLabs, Cartesia, or OpenAI TTS keys work the same way if the human already has one.

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

Every account the agent creates produces a password, and many ask for a second factor. The agent needs a place for both.

**Passwords.** Generate with `openssl rand -base64 24`. Store in the identity file under `accounts.<service>.password`, or in a Bitwarden vault owned by the agent (`bw` CLI, account created via Layer 6) if the human prefers a real vault. Never reuse a password across services.

**TOTP.** When a service offers an authenticator, take the setup secret from the QR page (the `otpauth://` URI or the plain secret) and store it under `accounts.<service>.totp_secret`. Generate codes with:

```bash
oathtool --totp -b <secret>
```

That makes the agent its own authenticator app, so 2FA never blocks it.

**Recovery codes.** Store under `accounts.<service>.recovery_codes`. They are the only way back in if a token is revoked.

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

- **Own calendar:** create a Google account at `accounts.google.com/signup` through the browser layer with the Layer 2 number for verification, or use a CalDAV calendar on any provider. Store the OAuth refresh token or app password under `calendar`.
- **Booking page:** Cal.com (`cal.com/signup`, API at `api.cal.com/v2`) gives the agent a public link like `cal.com/ari-vale/15min`. Put the link in email signatures and profiles.
- **Meetings:** Google Meet or Zoom links come from the calendar. The agent joins by voice (Layer 8) where the host supports it.

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

## Human touchpoints

The whole point is that setup runs without the human. These are the only places a person is needed, and each one is reached only when that layer is actually wanted:

| When | What | Why the agent cannot |
|------|------|----------------------|
| Before first run | An Orthogonal API key with credit | The marketplace account belongs to a person |
| Layer 4, Stripe live mode | Identity and bank details | Payouts require a legal person or entity |
| Layer 4, wallet | Fund the address once | Money has to come from somewhere |
| Layer 16, mailbox | Notarised USPS Form 1583 | Federal requirement, a person must sign |
| Layer 21 | Sign the formation documents | The entity's owner must be a person |
| Last step | Rules, if any | Only the human knows what they want |

Everything else, including every verification code, every 2FA setup, every account creation, every token, the agent does itself using its own inbox and number. If a step seems to need the human and is not in this table, look again: the code is in Layer 1 or Layer 2, the payment is Layer 4, and the browser is Layer 5.

## One-shot bootstrap

Run this top to bottom on a fresh agent. No pauses. Write to the identity file after each line.

1. Pick a name, check it is free on GitHub and AgentMail, write persona. (Layer 0)
2. Create the AgentMail inbox. (Layer 1)
3. AgentPhone sign-up with the inbox address, poll the inbox for the code, verify, store key and number. (Layer 2)
4. Generate the avatar mark and save it. (Layer 7)
5. Pick an ElevenLabs voice, set it on the AgentPhone agent. (Layer 8)
6. Generate an SSH key and a wallet. (Layers 10 and 4)
7. GitHub: browser sign-up with the inbox, code from the inbox, TOTP secret stored, fine-grained token created and verified, avatar uploaded. (Layers 6, 13, 7)
8. Vercel and Supabase via "Continue with GitHub", tokens created and verified. (Layer 6)
9. Supabase project for memory, `memories` and `people` tables created. (Layer 11)
10. Stripe account in test mode. (Layer 4)
11. Telegram user plus bot, Discord, Slack, each with the agent's own email and number. (Layer 3)
12. X and Reddit accounts with the avatar and persona. (Layer 14)
13. Cal.com booking page. (Layer 15)
14. Ask the human about rules and carry on. (Last step)

Steps 1 through 9 take one session with no input. Everything after is optional and can run when a task first needs it.

## Order of operations for a fresh agent

Follow the one-shot bootstrap above. After step 3 the agent can sign up for almost anything on its own. After step 8 it can build and ship software. After step 13 it can do most of what a person with a laptop and a phone can do.

## Last step: Ask the human for rules

Humanize ships with no rules of its own. When the base setup is done (steps 1 to 6), ask the human one question:

> Setup is done. Do you want to set any rules for how I use this identity? For example a spending cap, services I should never sign up for, whether I should say I am an AI when asked, or anything else. Say "none" to skip.

Do not block on the answer. Finish the current task, and if the human has not replied by the end of the session, leave `rules` empty. Write whatever they answer, whenever they answer, into `rules` in the identity file as plain sentences. Read `rules` at the start of every later task and follow them. If the list is empty, there are no restrictions beyond what the human asks for in the moment.

Suggested prompts if they want ideas, offered only if they ask:

- A monthly spend cap.
- Services or domains that are off limits.
- Whether to disclose being an AI on calls and emails.
- Which actions need a yes first (buying a number, deleting an inbox, releasing a number).
