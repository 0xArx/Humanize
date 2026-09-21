# Layer 19: Verify others

**Gives the agent:** the ability to check that someone else's phone or email is real, for example when it onboards users.
**Human needed:** none. **Cost:** $0.05 per successful phone check.
**Identity keys:** `verify.provider`

## Phone

AgentPhone (Layer 2) has verification endpoints:

```bash
curl -s -X POST https://api.agentphone.ai/v1/verify/send  -H "Authorization: Bearer <key>" -H "Content-Type: application/json" -d '{"to_number":"+1..."}'
curl -s -X POST https://api.agentphone.ai/v1/verify/check -H "Authorization: Bearer <key>" -H "Content-Type: application/json" -d '{"to_number":"+1...","code":"123456"}'
```

Read AgentPhone's skills page for the exact body fields before the first call; the two paths and the $0.05 price per successful check are from its documentation.

## Email

Send a random 6 digit code from the agent's own inbox (Layer 1), then compare what the person types back. No provider is needed.

```bash
python3 humanize.py set verify.provider "agentphone"
```

Identity and sanctions screening of people needs a regulated vendor with its own contract, which is outside what an agent can set up alone.
