# Layer 18: Signatures

**Gives the agent:** the ability to fill in and sign documents.
**Human needed:** an account with an e-signature service may need one. **Cost:** free tiers exist.
**Identity keys:** `accounts.esign`

- **Forms and PDFs, locally:** fill and flatten with `pypdf` (`pip install pypdf`) or `pdftk`, then send through Layer 1. No account.
- **Legally binding e-signatures:** Dropbox Sign (`https://api.hellosign.com/v3`) and DocuSign both have APIs. Sign up with the agent's email through the Layer 6 protocol; if a CAPTCHA or identity check appears, hand it to the human. Store the key in the vault.
- **A signature image** for documents that only need one: render the agent's name in any script font you have installed onto a transparent PNG, and keep it at `~/.humanize/signature.png`.
