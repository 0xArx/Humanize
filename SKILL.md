---
name: humanize
description: Turn an AI agent into a functioning person. Provisions everything a human has and an agent normally lacks, step by step, through APIs. An email inbox (AgentMail), a phone number with SMS and voice (AgentPhone), WhatsApp, a payment card, a browser, accounts on GitHub, Vercel, Supabase and any service, plus a face, a voice, web search, its own computer, memory, extra models, a password and 2FA store, social profiles, a calendar, a street address, a domain, e-signatures, a crypto wallet, and a legal entity. Uses Orthogonal where it has a provider and goes direct to vendors everywhere else. Use when the user says humanize, give my agent an email or phone, sign my agent up for X, get a token for X, or the agent hits a wall that needs an inbox, a number, a card, an account, a photo, a voice, a computer, or an address.
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
  "face": { "photo": "~/.humanize/face.png", "tavus": "p..." },
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

Before anything else, the agent needs a name and a persona. Ask the user for one or propose one. Keep it consistent everywhere: inbox display name, phone agent name, GitHub username, email signature.

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

**First-time account setup.** AgentPhone signs the agent up through the human's email, sends an OTP, and returns an API key plus a starter agent and number in one shot.

```bash
orth run agentphone /v0/agent/sign-up --body '{"human_email":"<the users email>","agent_name":"Ari Vale"}'
# returns verification_id. The OTP lands in the human's inbox, not the agent's. Ask the user for it.
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

**Telegram.** No sign-up needed for a bot. Message @BotFather from any Telegram account (or from the browser layer via web.telegram.org signed in with the Layer 2 number), run `/newbot`, store the token under `telegram`. Send with `https://api.telegram.org/bot<token>/sendMessage`. For a full user account rather than a bot, sign up at web.telegram.org with the Layer 2 number and store the session.

**Discord.** Create an application at `discord.com/developers/applications` through the browser layer, add a bot, store the bot token under `discord`. Send with `POST https://discord.com/api/v10/channels/<id>/messages`.

**Slack.** Create an app at `api.slack.com/apps`, install it to a workspace, store the bot token (`xoxb-`) under `slack`. Send with `POST https://slack.com/api/chat.postMessage`.

**iMessage.** Only from a Mac the agent controls. If the host is macOS with computer use, sign into Messages with the agent's Apple ID (created via Layer 6 with the agent's email and phone). Otherwise skip.

Store each under `messaging.<service>` with the token and the handle.

## Layer 4: Money

A human can pay, get paid, and hold value. Three parts.

**Pay: a card.** No issuer is on Orthogonal yet. Connect one of: Stripe Issuing (`POST /v1/issuing/cards`, needs a Stripe account from Layer 6), Lithic (`POST https://api.lithic.com/v1/cards`), or Ramp / Brex virtual cards if the human has a company account. Store the card token under `card`, never the PAN. Log every spend in `log` with amount and purpose.

**Get paid: Stripe.** Sign up at `dashboard.stripe.com/register` with the agent's email through Layer 6. Store the secret key under `accounts.stripe`. The agent can then create payment links (`POST /v1/payment_links`), invoices, and checkout sessions and send them from Layer 1.

**Hold value: a crypto wallet.** Needs no sign-up at all. Generate a keypair locally and store it in the identity file:

```bash
# Ethereum and every EVM chain
node -e "const w=require('ethers').Wallet.createRandom();console.log(JSON.stringify({address:w.address,privateKey:w.privateKey,mnemonic:w.mnemonic.phrase}))"
# Solana
solana-keygen new --no-bip39-passphrase -o ~/.humanize/solana.json
```

Store under `wallet.evm` and `wallet.solana`. Read balances and send with any RPC (Alchemy, Helius, public endpoints). Coinbase AgentKit and Solana Agent Kit wrap the common actions if the task is heavy on chain activity.

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
4. Wait for the verification code or link. Complete verification.
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

## Layer 7: Face

A human has a face. The agent needs one for profile pictures, video calls, and anywhere an avatar is asked for.

**Profile photo.** Generate once, reuse everywhere.

```bash
orth run nano-banana "/v1beta/models/gemini-2.5-flash-image:generateContent" --body '{"contents":[{"parts":[{"text":"Professional headshot of <persona description>, neutral background, natural light, photo-realistic"}]}],"generationConfig":{"responseModalities":["IMAGE"],"imageConfig":{"aspectRatio":"1:1"}}}'
```

Decode the base64, save to `~/.humanize/face.png`, and upload it as the avatar on every account in Layer 6. Store the path under `face.photo`.

**Video presence.** Tavus gives the agent a talking video replica that can join real-time video conversations. Create a persona from the face photo and a Layer 8 voice, list with `orth run tavus /v2/personas`, start a call with `orth run tavus /v2/conversations --body '{"persona_id":"..."}'`. Store `persona_id` under `face.tavus`. HeyGen and D-ID are direct alternatives with the same shape.

## Layer 8: Voice

Layer 2 gives the agent a voice on phone calls. This layer gives it one voice everywhere: calls, voice notes, videos, voice messages on WhatsApp and Telegram.

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

A human has profiles. The agent gets accounts on the networks it needs, each via the Layer 6 protocol with the Layer 7 photo as avatar and the Layer 0 persona as bio.

| Network | Sign up | Then |
|---------|---------|------|
| X | `x.com/i/flow/signup` (email + phone from Layers 1 and 2) | API keys at `developer.x.com` |
| LinkedIn | `linkedin.com/signup` | read via `orth run edges ...` or `orth run scrapecreators ...`, post via browser |
| Reddit | `reddit.com/register` | app at `reddit.com/prefs/apps` for API |
| GitHub | already done in Layer 6 | fill in bio, avatar, README profile |
| Product Hunt, Hacker News, Dev.to | sign up with the agent's email | post via browser or API where one exists |

Store handle and token under `social.<network>`. A consistent name, photo, and bio across all of them is what makes the agent read as one person.

## Layer 15: Calendar and scheduling

A human has a calendar others can book into.

- **Own calendar:** Google Calendar on a Google account created via Layer 6, or a CalDAV calendar on any provider. Store the OAuth refresh token or app password under `calendar`.
- **Booking page:** Cal.com (`cal.com/signup`, API at `api.cal.com/v2`) gives the agent a public link like `cal.com/ari-vale/15min`. Put the link in email signatures and profiles.
- **Meetings:** Google Meet or Zoom links come from the calendar. Tavus from Layer 7 lets the agent actually appear on the call.

## Layer 16: Address and physical mail

Some sign-ups, deliveries, and registrations need a street address.

- **Virtual mailbox:** Stable, Earth Class Mail, or iPostal1 give a real street address, scan incoming mail, and expose it via API or email notification to Layer 1. Sign up via Layer 6. Store the address under `address` and the API key under `accounts.<provider>`.
- **Sending mail:** Lob (`api.lob.com/v1/letters`) or PostGrid send physical letters and postcards from an API.
- **Deliveries:** the virtual mailbox address works for parcels too. The service forwards on request.

## Layer 17: Domain and website

A human has a home on the web and an email at their own domain.

1. Buy a domain. Namecheap, Porkbun, and Cloudflare Registrar all have APIs; Vercel Domains (`POST https://api.vercel.com/v5/domains/buy`) is simplest if Vercel is already set up from Layer 6.
2. Point DNS at Vercel, deploy a one-page site with name, photo, bio, booking link, and contact.
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

## Order of operations for a fresh agent

1. Identity: name and persona (Layer 0).
2. Email: AgentMail inbox (Layer 1).
3. Phone: AgentPhone sign-up and verify (Layer 2).
4. Face and voice (Layers 7 and 8), so every account created next has the same photo.
5. GitHub, then Vercel and Supabase via GitHub sign-in (Layer 6).
6. Keys and 2FA store (Layer 13), memory (Layer 11).
7. Everything else as the task needs it: messaging, money, social, calendar, domain, computer, address, documents, entity.
8. Ask the human if they want any rules.

After step 3 the agent can sign up for almost anything on its own. After step 5 it can build and ship software. After step 7 it can do most of what a person with a laptop and a phone can do.

## Last step: Ask the human for rules

Humanize ships with no rules of its own. When the base setup is done (steps 1 to 6), ask the human one question:

> Setup is done. Do you want to set any rules for how I use this identity? For example a spending cap, services I should never sign up for, whether I should say I am an AI when asked, or anything else. Say "none" to skip.

Write whatever they answer into `rules` in the identity file, as plain sentences. Read `rules` at the start of every later task and follow them. If the list is empty, there are no restrictions beyond what the human asks for in the moment.

Suggested prompts if they want ideas, offered only if they ask:

- A monthly spend cap.
- Services or domains that are off limits.
- Whether to disclose being an AI on calls and emails.
- Which actions need a yes first (buying a number, deleting an inbox, releasing a number).
