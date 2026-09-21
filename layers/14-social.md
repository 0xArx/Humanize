# Layer 14: Social

**Gives the agent:** public profiles.
**Human needed:** yes, once per network. **Cost:** free.
**Identity keys:** `social.<network>.handle`, `social.<network>.token`

X, LinkedIn and Reddit all show CAPTCHAs at sign-up and forbid automated account creation, so a person creates each one. Prepare everything so it takes a minute: the agent's email and number, a free handle, the avatar file (Layer 7), the persona as the bio. The human clicks through the CAPTCHA; the confirmation code goes to the agent's inbox.

| Network | After the account exists |
|---------|--------------------------|
| X | Create an app at developer.x.com for API keys. |
| Reddit | Create an app at reddit.com/prefs/apps for API access. |
| LinkedIn | No open posting API for individuals; the agent reads through the browser and posts through it. |
| GitHub | Layer 6. Fill in the bio and avatar. |

If the human connects the accounts once in the Mailgent console (Settings, Integrations), the agent can post with `mailgent social post "<text>" --platforms x,linkedin` and read with `mailgent social accounts` and `mailgent social posts`.

A consistent name, avatar and bio across all of them is what makes the agent read as one person.
