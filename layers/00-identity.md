# Layer 0: Identity

**Gives the agent:** a name, a persona, and a cryptographic identity of its own.
**Human needed:** none. **Cost:** free.
**Identity keys:** `name`, `persona`, `did`

## Steps

1. Pick a plausible full name and a two line persona. Do not wait for the human. They can rename the agent from the dashboard at any time.
2. Check the handle is free where it matters. This is a public lookup that needs no account:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://github.com/<handle>     # 404 means free, 200 means taken
   ```
   AgentMail and Mailgent tell you at sign-up if a username is taken (Layer 1).
3. Create the identity and start the dashboard:
   ```bash
   python3 humanize.py init --name "<name>" --persona "<persona>"
   ```
4. The DID arrives with the Mailgent sign-up in Layer 1. Store it:
   ```bash
   python3 humanize.py set did "<did>"
   ```

Keep the name identical everywhere it appears: inbox display name, phone agent name, GitHub username, signatures.

If the human renames the agent from the dashboard, update the display name on every account. The avatar does not change; it is seeded once (Layer 7).
