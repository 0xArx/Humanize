# Layer 6: Accounts

**Gives the agent:** accounts on the services a task needs, each with a token it can use.
**Human needed:** a CAPTCHA on some services, see below. **Cost:** free tiers.
**Identity keys:** `accounts.<service>.username`, `accounts.<service>.vault`

## The protocol, for any service

1. Check the identity file. If the account exists and its token still works, stop.
2. Look for an API or CLI sign-up. Prefer it over the browser.
3. Sign up with the agent's own email (Layer 1) and phone (Layer 2). Never the human's.
4. Poll Layer 1 or 2 for the code or link and complete verification. Do not ask the human for it.
5. Create the narrowest token that does the job, named `humanize-<agent name>`. If the service offers 2FA, enable it and put the secret in the vault (Layer 13).
6. Verify the token with one real read call.
7. Store the username in the identity file and the secret in the vault:
   ```bash
   python3 humanize.py set accounts.<service>.username "<username>"
   python3 humanize.py set accounts.<service>.vault "<vault entry name>"
   python3 humanize.py log "<service> account created"
   ```

## GitHub

GitHub forbids accounts registered by automated methods and shows a CAPTCHA at sign-up, so a person creates this one. It is the single most useful handoff, because a private repo is where the agent stores itself (Layer 23), and Vercel and Supabase both offer "Continue with GitHub".

The agent prepares everything: a username that is free (Layer 0), the agent's email, a generated password already stored in the vault, and the avatar file. The human opens `https://github.com/signup`, pastes those in, and clicks the CAPTCHA. About two minutes. The confirmation code goes to the agent's inbox.

Then the agent does the rest with the browser:

- Token: `https://github.com/settings/personal-access-tokens/new`, fine-grained, scoped to what the task needs. The password (from the vault) is asked for once.
- Verify: `curl -s -H "Authorization: Bearer <token>" https://api.github.com/user`
- Everything after that is API: create repos, push over HTTPS with the token, and so on.

If the human already has a GitHub account and would rather not make a second one, they create an empty private repository and a fine-grained token limited to that repo (Contents: read and write). That is enough for Layer 23.

## Vercel and Supabase

After GitHub exists, use "Continue with GitHub". Either may ask for a phone verification: use the Layer 2 number and read the code from Layer 2.

- Vercel token: `https://vercel.com/account/tokens`. Verify with `curl -s -H "Authorization: Bearer <token>" https://api.vercel.com/v2/user`. Deploy with `npx vercel deploy --prod --yes --token <token>`.
- Supabase token: `https://supabase.com/dashboard/account/tokens` (a personal access token, prefix `sbp_`). Verify with `curl -s -H "Authorization: Bearer <pat>" https://api.supabase.com/v1/organizations`. Create projects with `POST /v1/projects`, run SQL with `POST /v1/projects/<ref>/database/query`.

## Other services

Try the protocol. If a CAPTCHA appears, treat it as a handoff (Layer 5). Add the working recipe to this file once it works so the next agent does not rediscover it.

> Status (2026-09-21): token URLs and verify calls are the vendors' documented endpoints; none exercised.
