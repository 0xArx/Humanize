# Layer 2: Phone

**Gives the agent:** a real number that receives SMS (so it can pass phone verification), sends SMS, and makes and takes voice calls.
**Human needed:** none for AgentPhone. **Cost:** a $5 sign-up credit covers the first month of the starter number, then $3 a month per number.
**Identity keys:** `phone.agentphone.number`, `.number_id`, `.agent_id`, `.api_key`

## AgentPhone (primary, US and Canada)

The sign-up sends a 6 digit code to whatever email you give it. Give it the agent's own inbox from Layer 1.

```bash
curl -s -X POST https://api.agentphone.ai/v0/agent/sign-up -H "Content-Type: application/json" \
  -d '{"human_email":"<agent email>","agent_name":"<name>"}'
# returns verification_id (valid 10 minutes). 409 means that email already has an account.
# read the 6 digit code from the agent's inbox, then:
curl -s -X POST https://api.agentphone.ai/v0/agent/verify -H "Content-Type: application/json" \
  -d '{"verification_id":"<id>","otp_code":"123456"}'
# returns account_id, agent_id, number_id, phone_number and api_key (the key is shown once)
```

Store all of it:

```bash
python3 humanize.py set phone.agentphone.number "<phone_number>"
python3 humanize.py set phone.agentphone.number_id "<number_id>"
python3 humanize.py set phone.agentphone.agent_id "<agent_id>"
python3 humanize.py set phone.agentphone.api_key "<api_key>"
python3 humanize.py log "agentphone number provisioned" --cost '$5 credit'
```

Every other call sends `Authorization: Bearer <api_key>` to `https://api.agentphone.ai`:

| Do | Call |
|----|------|
| Read inbound SMS, including OTPs | `GET /v1/numbers/<number_id>/messages` |
| Send an SMS | `POST /v1/messages` with `agent_id`, `to_number`, `body` |
| Place a call | `POST /v1/calls` with `agentId`, `toNumber`, `systemPrompt`, `initialGreeting`; then `GET /v1/calls/<callId>` for the transcript |
| List voices, choose one | `GET /v1/agents/voices`, then `PATCH /v1/agents/<agentId>` with `voice` |
| Push inbound events to a URL | `POST /v1/agents/<agentId>/webhook` |
| Buy another number | `POST /v1/numbers` with `country`, `areaCode`, `agentId` |

The first SMS to a new contact must say who is sending, confirm they opted in, and say how to opt out ("Reply STOP to unsubscribe"). Carriers silently drop messages that skip this.

## Dial (optional: non-US numbers, iMessage)

Dial's own docs describe a sign-up that needs an email code and then a verified, SMS-capable phone number that is not itself a Dial number, described as one the user keeps. The agent's AgentPhone number satisfies "SMS-capable and not a Dial number". Whether Dial accepts an agent-owned number is not documented, so treat this as a try, and fall back to a human's phone if it refuses.

```bash
npm install -g @getdial/cli
dial auth login <agent email>                              # emails a code
dial auth verify-otp --code <emailed code> --agent claude-code     # or codex, cursor, ...
dial auth register-number <AgentPhone number>              # sends an SMS code to that number
dial auth verify-otp --number --code <code from AgentPhone messages>
dial wait-for message.received -f channel=sms              # blocks until an SMS arrives
```

On success Dial writes its key to `~/.local/share/dial/auth.json` (mode 600) and gives a $5 credit; numbers cost $3 a month plus usage. If a step's output includes an `agentHint` telling you to ask the user, do that. Skip Dial entirely unless you need a non-US number or iMessage.

> Status (2026-09-21): AgentPhone endpoints and Dial commands read from the vendors' own docs; hosts respond and both npm packages exist. Not exercised live. The AgentPhone-number-as-Dial-verification step is an inference. See docs/providers.md.
