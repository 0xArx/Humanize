# Layer 3: Messaging

**Gives the agent:** reachability on the apps people actually use.
**Human needed:** depends on the service, see the table. **Cost:** free unless noted.
**Identity keys:** `messaging.<service>.token`, `whatsapp.status`, `whatsapp.number`

Be honest with yourself about which of these can be done alone. Anything that shows a CAPTCHA, asks for a business document, or rejects virtual numbers is a human step (see the touchpoints in SKILL.md).

| Service | Can the agent do it alone? | Notes |
|---------|----------------------------|-------|
| SMS | Yes | Layer 2 |
| iMessage | Yes, through Dial | Layer 2, Dial section. Each iMessage number can start 50 new conversations a day. |
| Slack | Usually | Sign up at slack.com with the agent's email (a code arrives by email), create a workspace, create an app at api.slack.com/apps, install it, store the `xoxb-` bot token. Send with `POST https://slack.com/api/chat.postMessage`. |
| Telegram | Maybe | A bot needs a Telegram account, which needs a phone number and SMS code. Telegram often rejects virtual numbers. If it accepts the Layer 2 number: message @BotFather, send `/newbot`, store the token. Send with `https://api.telegram.org/bot<token>/sendMessage`. |
| Discord | No | Sign-up shows a CAPTCHA. After a human creates the account, the agent can create an application and bot at discord.com/developers/applications and store the bot token. Send with `POST https://discord.com/api/v10/channels/<id>/messages`. |
| WhatsApp | No | The WhatsApp Business Platform needs a verified Meta business. If the human has one: register the Layer 2 number, read the SMS code from Layer 2, store the access token and phone number ID, send with `POST https://graph.facebook.com/v21.0/<phone_number_id>/messages`. Mark `whatsapp.status` as `not_provisioned`, `pending` or `active`. |

Store each working service:

```bash
python3 humanize.py set messaging.telegram.token "<token>"
python3 humanize.py log "telegram bot created"
```
