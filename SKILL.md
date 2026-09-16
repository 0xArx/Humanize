---
name: humanize
description: Turn an AI agent into a functioning person. Provisions everything a human has and an agent normally lacks, step by step, through APIs. An email inbox (AgentMail), a phone number with SMS and voice (AgentPhone), WhatsApp, a payment card, a browser it can drive (Notte), and accounts on services like GitHub, Vercel, and Supabase, including sign-up, verification codes, and API tokens. Uses Orthogonal to find and call each provider. Use when the user says humanize, give my agent an email or phone, sign my agent up for X, get a token for X, or the agent hits a wall that needs an inbox, a number, a card, or an account.
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
  "browser": { "provider": "notte" },
  "accounts": {
    "github": { "username": "arivale", "token": "ghp_...", "created": "2026-09-16" },
    "vercel": { "token": "...", "team_id": "..." },
    "supabase": { "pat": "sbp_...", "org_id": "..." }
  },
  "log": [ { "at": "2026-09-16T10:00:00Z", "did": "created agentmail inbox", "cost": "$2/mo" } ]
}
```

Every credential the agent earns goes in here. Every cost goes in `log`. The user can read this file at any time and see exactly what their agent is and what it has.

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

If Orthogonal has it, use it through `orth run`. If it does not, use the provider's own API with a key from the identity file. If there is no API at all, use the browser layer.

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

Cost: $3 per month per number. Ask before buying.

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

## Layer 3: WhatsApp

WhatsApp rides on the phone number from Layer 2. Register the AgentPhone number with the WhatsApp Business Platform, receive the SMS verification code through Layer 2, and store the WhatsApp token in the identity file.

Orthogonal does not have a dedicated WhatsApp provider yet. Check with `orth search "whatsapp"` each time before falling back to Meta's Cloud API directly. Mark `whatsapp.status` as `pending`, `active`, or `not_provisioned`.

## Layer 4: Money (card)

A card lets the agent pay for the things above and for anything else the user approves.

No card issuer is on Orthogonal yet. Search `orth search "virtual card"` first. If nothing, this layer stays `not_provisioned` until the user connects an issuer of their choice.

Rules that apply regardless of provider:

- The agent never touches the user's own bank, card, or wallet. It uses only a card that was issued to the agent with a limit the user set.
- Every spend is logged in the identity file with amount and purpose.
- Any new recurring charge, and any single charge above the limit the user set, is asked about first. Stored keys are not permission to spend.

## Layer 5: Hands (browser via Notte)

For any service with no sign-up API, the agent uses a real browser.

```bash
orth run notte /sessions/start --body '{"headless":true,"browser_type":"chromium"}'
orth run notte /agents/start --body '{"session_id":"<id>","url":"https://example.com/signup","task":"Sign up with email ari.vale@agentmail.to and name Ari Vale. Stop when a verification email is mentioned."}'
orth run notte "/agents/<agent_id>"                 # poll for result
orth run notte "/sessions/<session_id>/page/screenshot"
orth run notte "/sessions/<session_id>/cookies"     # save session for later
```

Keep `solve_captchas` off. If a sign-up flow blocks with a CAPTCHA, stop and hand that one step to the user. Do not route around it.

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

## Guardrails

- One identity per human. The agent is one person, not a crowd. Never create multiple accounts on one service to get around limits.
- Say what you are when asked. If a human on a call or in an email asks whether they are talking to an AI, answer honestly.
- Money is never assumed. Every new monthly cost and every purchase gets a yes from the user first, even if the key is already stored.
- No CAPTCHA bypass, no scraping past a login wall the agent does not own, no use of the user's personal credentials anywhere.
- Irreversible actions (release a number, delete an inbox, delete an account) need a yes from the user first.
- Keep the identity file local. Never commit it, never put it in an env var on a deployed app, never paste it into a chat.

## Order of operations for a fresh agent

1. Identity: name and persona.
2. Email: AgentMail inbox.
3. Phone: AgentPhone sign-up and verify.
4. GitHub.
5. Vercel and Supabase, both via GitHub sign-in.
6. WhatsApp, card, and anything else, as the task needs them.

After step 3 the agent can sign up for almost anything on its own. After step 5 it can build and ship software. The rest is added when needed.
