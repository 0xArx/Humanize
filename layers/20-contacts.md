# Layer 20: Contacts

**Gives the agent:** a list of people it knows, and ways to find people it does not.
**Human needed:** none for the free sources. **Cost:** free, or cents per lookup.
**Identity keys:** `contacts.source`, `contacts.table`

Keep the people it has met in local memory (Layer 11):

```bash
python3 humanize.py memory person "<name>" --handle "<handle>" --notes "<how you met, what they want>"
python3 humanize.py memory people
python3 humanize.py set contacts.source "memory"
```

## Finding someone

In order of cost:

1. **Free, no account.** The host's web search (Layer 9). For developers, GitHub's API needs no key for light use: `curl -s https://api.github.com/users/<login>` and `curl -s "https://api.github.com/search/users?q=<name>+in:fullname"` (60 requests an hour unauthenticated).
2. **One signup, many sources: Apify (Layer 9).** Ready-made Actors cover LinkedIn profiles, company pages, Google Maps businesses and social profiles from one token and $5 of free monthly credit.
3. **Pay per lookup with no signup: the x402 Bazaar (Layer 9).** The live catalog on 2026-09-21 included a people-search provider (`stableenrich.dev`, about 15 cents a call) and Exa web search (`api.exa.ai`). Filter the catalog for the host you want and call it with `mailgent pay`.
4. **A verified email finder** such as Hunter has a free plan of 25 searches a month; sign up through the Layer 6 protocol and store the key in the vault.

Do not pile up per-vendor accounts. Start at 1 and move down only when the free option genuinely cannot answer.
