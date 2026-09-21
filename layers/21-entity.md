# Layer 21: Entity

**Gives the agent:** a company to sign contracts, invoice and hold a bank account under, if it ever needs one.
**Human needed:** yes, they sign. **Cost:** a formation fee.
**Identity keys:** `entity.name`

Stripe Atlas, Firstbase and doola form a US LLC or C-corp from a web form and return an EIN. The owner of the entity must be a person, so this is the human's decision and signature. The agent fills the forms with the browser (Layer 5), stops at the signature, and stores the result:

```bash
python3 humanize.py set entity.name "<company name>"
python3 humanize.py log "entity formed"
```

The registered agent address on the paperwork can double as the Layer 16 address.
