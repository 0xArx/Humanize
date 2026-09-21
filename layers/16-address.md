# Layer 16: Address

**Gives the agent:** a street address for sign-ups, deliveries and registrations.
**Human needed:** yes, a notarised form. **Cost:** a monthly mailbox fee.
**Identity keys:** `address.line1`, `address.city`, `address.provider`

A virtual mailbox (Stable, Earth Class Mail, iPostal1) gives a real street address, scans incoming mail and notifies by email, which lands in Layer 1. Parcels can be forwarded on request.

United States rules (USPS Form 1583) require a notarised ID from a real person before a mailbox activates. The agent fills in everything else, pays with the card from Layer 4, and hands the human exactly one thing to do: sign and notarise the form. Then:

```bash
python3 humanize.py set address.line1 "<street>"
python3 humanize.py set address.city "<city>"
python3 humanize.py set address.provider "<provider>"
mailgent vault store-address home --recipient "<name>" --line1 "<street>" --city "<city>" --state "<st>" --postcode "<zip>" --country US
```

To send physical letters from an API, Lob (`POST https://api.lob.com/v1/letters`) and PostGrid both work; each needs an account and a payment method (Layer 4).
