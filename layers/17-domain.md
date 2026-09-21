# Layer 17: Domain

**Gives the agent:** a home on the web and email at its own domain.
**Human needed:** a payment card, see Layer 4. **Cost:** a domain costs roughly ten dollars a year.
**Identity keys:** `domain.name`, `domain.registrar`

1. Buy a domain with the Layer 4 card. Cloudflare Registrar sells at cost; Namecheap, Porkbun and Vercel Domains all have APIs. Each needs an account and a payment method, so this is a handoff when no card exists yet.
2. Point DNS at wherever the site lives and deploy a one page site with the name, avatar, bio, booking link (Layer 15) and contact.
3. Email at the domain: AgentMail can create an inbox on a verified custom domain (the create-inbox call takes a `domain` field). Add the DNS records AgentMail asks for, wait for verification, then create `<handle>@<domain>`.
4. Record it:
   ```bash
   python3 humanize.py set domain.name "<domain>"
   python3 humanize.py set domain.registrar "<registrar>"
   ```
