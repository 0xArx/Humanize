# Layer 1: Email

**Gives the agent:** an inbox it can read and send from. Almost every sign-up sends a code or a link here.
**Human needed:** yes, once, briefly: a real email address and one relayed code. **Cost:** free tier.
**Identity keys:** `email.agentmail.address`, `email.agentmail.api_key`

AgentMail (YC-backed, [agentmail.to](https://agentmail.to)) is the only provider here. Its free plan is 3 inboxes and 3,000 emails a month.

## The one unavoidable human step in this whole skill

AgentMail's own sign-up sends its verification code to **the human's real email address**, by design ("Email address of the human who owns the agent. A 6-digit OTP will be sent to this address."). That is not a trick to route around: it is how AgentMail confirms a real person is behind the agent, and it is the only place in Humanize where the agent cannot bootstrap itself without a person. Do it once, up front, before anything else:

```bash
curl -s -X POST https://api.agentmail.to/v0/agent/sign-up -H "Content-Type: application/json" \
  -d '{"human_email":"<the humans real email>","username":"<handle>"}'
# returns organization_id, inbox_id (<handle>@agentmail.to) and api_key. Store the key now, it is not shown again.
python3 humanize.py set email.agentmail.address "<inbox_id>"
python3 humanize.py set email.agentmail.api_key "<api_key>"
```

Ask the human for the 6 digit code that lands in their own inbox, then verify:

```bash
curl -s -X POST https://api.agentmail.to/v0/agent/verify -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" -d '{"otp_code":"123456"}'
```

Until verified, the inbox can only send to the human's address; verification lifts that and applies the free plan. Sign-up is idempotent: calling it again with the same `human_email` rotates the key, so do not repeat it once a key is stored.

After this one code, the agent never asks the human for another verification code again: every later sign-up (Layer 2 and onward) sends its OTP to this AgentMail inbox, which the agent reads itself.

## Reading and sending

```bash
curl -s -H "Authorization: Bearer <api_key>" "https://api.agentmail.to/v0/inboxes/<inbox_id>/messages?limit=10"
curl -s -X POST -H "Authorization: Bearer <api_key>" -H "Content-Type: application/json" \
  "https://api.agentmail.to/v0/inboxes/<inbox_id>/messages/send" -d '{"to":["x@y.com"],"subject":"Hi","text":"Hello"}'
```

The `agentmail` command line tool and Python/Node SDKs wrap the same API if a host prefers them over curl.

## Waiting for a verification code

Once this inbox exists, poll it every 5 seconds for up to 2 minutes for anything after it. Match the sender to the service just signed up for. Take the 6 to 8 digit code, or the first link containing `verify`, `confirm` or `activate`. Do not ask the human for any of these; they are always in the agent's own inbox from here on.

> Status (2026-09-22): endpoints and the sign-up/verify field names are read from AgentMail's own API reference and confirmed reachable. A live sign-up was not exercised, so treat the first real run as the last check. An earlier draft of this layer bootstrapped through a second, unvetted provider to avoid asking the human for anything at all; that provider's tooling did not hold up (see docs/providers.md) and is gone. See docs/providers.md for what has and has not been checked.
