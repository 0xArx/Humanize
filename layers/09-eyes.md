# Layer 9: Eyes

**Gives the agent:** search, page reading, weather and local places.
**Human needed:** none for the free tools; funding for the paid ones. **Cost:** free, or cents per call.
**Identity keys:** `eyes.search`, `eyes.weather`

## Free, no account, no key (all returned 200 on 2026-09-21)

| Need | Use |
|------|-----|
| Search the web | The host's own search tool first (Claude Code WebSearch and WebFetch, Codex web search). Otherwise `curl -s -A "<agent name>" "https://html.duckduckgo.com/html/?q=<query>"` and read the results. |
| Read a page as clean text | `curl -s https://r.jina.ai/<full URL>` returns markdown. |
| Weather | `curl -s "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.12&current=temperature_2m"`; find coordinates with `https://geocoding-api.open-meteo.com/v1/search?name=London&count=1`. |
| Find a place or business | `curl -s -A "<agent name>" "https://nominatim.openstreetmap.org/search?q=dentist+london&format=json&limit=5"`. Send a real User-Agent and stay under one request a second. |
| Look something up | `curl -s https://en.wikipedia.org/api/rest_v1/page/summary/<Title>` |

```bash
python3 humanize.py set eyes.search "host web tools"
python3 humanize.py set eyes.weather "open-meteo"
```

## When those are not enough

**Apify: one signup, thousands of scrapers.** One account and one token give access to over 70,000 ready-made scrapers (Google Maps, Instagram, Amazon, LinkedIn and more), with $5 of free credit every month and no card. That replaces a separate signup for each site. Sign up at apify.com (email or GitHub; treat a CAPTCHA as a handoff, Layer 5), create a token at Console, Settings, Integrations, and store it in the vault.

```bash
curl -s -X POST "https://api.apify.com/v2/actors/compass~google-maps-extractor/run-sync-get-dataset-items" \
  -H "Authorization: Bearer <apify token>" -H "Content-Type: application/json" -d '{"searchStringsArray":["dentist London"],"maxCrawledPlacesPerSearch":5}'
```

The synchronous call returns the dataset items and times out at 300 seconds; use the run endpoints for longer jobs. Input fields differ per Actor, so read the Actor's page first.

**The x402 Bazaar: pay per call, no account at all.** Your Mailgent wallet (Layer 4) can pay any x402 service. Coinbase's public catalog lists them and needs no key:

```bash
curl -s "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100&offset=0" | python3 -m json.tool | head -60
```

It held 15,141 endpoints on 2026-09-21, including Exa web search and a people-enrichment provider, at prices from a fraction of a cent to about 15 cents a call. The `query` parameter had no effect when tested, so page with `limit` and `offset` and filter the `resource` and `description` fields yourself. Call one with `mailgent pay <resource url>`. The human funds the wallet once, in small amounts, and only when a paid lookup is worth it.

> Status (2026-09-21): every free endpoint above answered 200; the Bazaar catalog answered with 15,141 entries. Apify's endpoint is from its API docs. No paid call was made.
