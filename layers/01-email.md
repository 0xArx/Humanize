# Layer 1: Email

**Gives the agent:** an inbox it can read and send from. Almost every sign-up sends a code or a link here.
**Human needed:** none. **Cost:** free tiers.
**Identity keys:** `email.mailgent.address`, `email.mailgent.api_key`, `email.agentmail.address`, `email.agentmail.api_key`, `did`, `wallet.mailgent_base_usdc`

Two agent-native providers. Mailgent needs nothing to start, so it goes first. AgentMail gives a conventional address people recognise.

## Mailgent: one call, no email, no human

```bash
curl -s -X POST https://api.mailgent.dev/v0/agent-signup -H "Content-Type: application/json" -d '{}'
```

The vendor documents that this returns an address (for example `bright-otter-k3f9@mailgent.dev`), an API key (`mgnt-...`), a DID with a signing keypair, an encrypted vault, a calendar and a USDC wallet on Base. Read the JSON it returns and store each value; do not guess field names.

```bash
python3 humanize.py set email.mailgent.address "<address>"
python3 humanize.py set email.mailgent.api_key "<mgnt-...>"
python3 humanize.py set did "<did>"
python3 humanize.py set wallet.mailgent_base_usdc "<0x...>"
python3 humanize.py log "mailgent sign-up"
```

Then install the command line tool (Node 18 or newer) and check it works:

```bash
npm install -g @mailgent-dev/cli
export MAILGENT_API_KEY="$(python3 humanize.py get email.mailgent.api_key)"
mailgent whoami
mailgent mail list --limit 20 --labels inbox --json
mailgent mail get <messageId> --json
mailgent mail send --to a@b.com --subject "Hi" --text "Hello"
mailgent mail reply <messageId> --text "Reply"
```

There is also an MCP server at `https://api.mailgent.dev/mcp` (authenticated with the same key) for hosts that prefer tools over a shell.

## AgentMail: the address people see

Free plan: 3 inboxes and 3,000 emails a month. Sign up with the Mailgent address as `human_email`. The 6 digit code goes to that inbox, which the agent already reads.

```bash
curl -s -X POST https://api.agentmail.to/v0/agent/sign-up -H "Content-Type: application/json" \
  -d '{"human_email":"<mailgent address>","username":"<handle>"}'
# returns organization_id, inbox_id (<handle>@agentmail.to) and api_key. Store the key now, it is not shown again.
python3 humanize.py set email.agentmail.address "<inbox_id>"
python3 humanize.py set email.agentmail.api_key "<api_key>"

# read the 6 digit code from the Mailgent inbox, then:
curl -s -X POST https://api.agentmail.to/v0/agent/verify -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" -d '{"otp_code":"123456"}'
```

Until verified, the inbox can only send to the `human_email`. Verification lifts that and applies the free plan. Sign-up is idempotent: calling it again with the same `human_email` rotates the key, so do not repeat it once you have stored a key.

Read and send with the same base URL and the bearer key:

```bash
curl -s -H "Authorization: Bearer <api_key>" "https://api.agentmail.to/v0/inboxes/<inbox_id>/messages?limit=10"
curl -s -X POST -H "Authorization: Bearer <api_key>" -H "Content-Type: application/json" \
  "https://api.agentmail.to/v0/inboxes/<inbox_id>/messages/send" -d '{"to":["x@y.com"],"subject":"Hi","text":"Hello"}'
```

If AgentMail rejects the Mailgent domain as the `human_email` (a 400 whose `fix` field says what to do), skip AgentMail. The Mailgent inbox is enough for everything else.

## Waiting for a verification code

Poll the inbox every 5 seconds for up to 2 minutes. Match the sender to the service you just signed up for. Take the 6 to 8 digit code, or the first link containing `verify`, `confirm` or `activate`. Do not ask the human for a code; it is always in one of the agent's own inboxes.

> Status (2026-09-21): endpoints, packages and commands checked against the vendors' own documentation; hosts respond. A live sign-up was not exercised. See docs/providers.md.
