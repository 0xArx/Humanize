# Layer 0: Identity

**Gives the agent:** a name, a persona and a business card.
**Human needed:** none. **Cost:** free.
**Identity keys:** `name`, `persona`, `business_card.title`, `business_card.tagline`, `business_card.website`

## Steps

1. Pick a plausible full name and a two line persona. Do not wait for the human. They can rename the agent from the dashboard at any time.
2. Check the handle is free where it matters. This is a public lookup that needs no account:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://github.com/<handle>     # 404 means free, 200 means taken
   ```
   AgentMail tells you at sign-up if a username is taken (Layer 1).
3. Create the identity and start the dashboard:
   ```bash
   python3 humanize.py init --name "<name>" --persona "<persona>"
   ```
4. After the inbox (Layer 1) and phone number (Layer 2) exist, and again whenever the name, number, email, domain or handles change, generate the business card:
   ```bash
   python3 humanize.py card
   ```
   Pass `--title`, `--tagline` and `--website` the first time to set those fields. They are saved to `business_card` in the identity file and used on every later run.

Keep the name identical everywhere it appears: inbox display name, phone agent name, GitHub username, signatures.

If the human renames the agent from the dashboard, update the display name on every account and regenerate the card. The avatar does not change; it is seeded once (Layer 7).

## The business card

Running `python3 humanize.py card` writes four files to `$HUMANIZE_HOME/card/`:

| File | What it is |
|------|------------|
| `card.vcf` | A full vCard 3.0 contact file. Attach it to emails, link it from profiles, or import it directly into a contacts app. |
| `front.png` | The front face of the card, 1050 x 600 px (3.5 x 2 in at 300 dpi). The agent's name, title, tagline, and a two-column contact grid. |
| `back.png` | The back face. A QR code that, when scanned with a phone camera, offers to save the agent as a contact. The QR payload is a compact vCard. |
| `card.pdf` | Two-page PDF at 3.5 x 2 in. Ready to send to a print shop. Note: this is the trim size with no bleed. A print shop will ask for 1/8 in of bleed on each edge; add it in the shop's template or ask them to add it. |

The avatar ribbons appear as the brand mark on both faces.

### Setting the optional fields

```bash
python3 humanize.py card --title "AI Agent" --tagline "Direct. Ships small things fast." --website "https://arivale.ai"
```

These write `business_card.title`, `business_card.tagline` and `business_card.website` to the identity file. After that first call, run `python3 humanize.py card` alone to regenerate with the saved values.

You can also set them directly:

```bash
python3 humanize.py set business_card.title "AI Agent"
python3 humanize.py set business_card.tagline "Direct. Ships small things fast."
python3 humanize.py set business_card.website "https://arivale.ai"
```

### What is on the card

The card reads `email`, `phone`, `domain`, `social` and `calendar` from the identity file. Fields that exist appear; fields that are missing are left out. A card never contains secrets, only addresses, numbers and public handles. If none of the contact fields exist, the card renders with just the name and a note is printed at the end of the command's output.

### Handing it out

- **Email**: attach `card.vcf` to an email or link to it from a signature. Recipients click it to import the contact.
- **Print**: send `card.pdf` to a print shop. Standard business-card size is 3.5 x 2 in.
- **Sharing**: scan the QR code on the back with any phone camera to save the contact.

## No vendor-issued identity

An earlier draft of this layer generated a "DID" through a third-party sign-up. It was removed: that provider's own client tooling could not reliably sign or verify anything on a stock machine (see docs/providers.md), and a cryptographic identity that does not actually work is worse than none. A name, a persona, and the stable internal namespace the secret store already keeps per agent (`keystore.ns`, used to keep two agents on one machine from sharing a secret) are what Layer 0 promises. If a real, working self-sovereign identity is added later, it will be generated with a properly vetted library, not a hand-rolled one, and this file will say so.
