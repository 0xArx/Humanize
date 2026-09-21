# Contributing

Read `AGENTS.md` for the rules. In short:

```bash
python3 -m unittest discover -s tests      # about two minutes; every test uses a throwaway data folder
python3 humanize.py doctor                 # checks an install
python3 humanize.py demo                   # look at the dashboard on a sample agent
```

- The tests must pass, and a bug fix ships with a test that fails without it.
- Standard library only. No package manifest, no build step.
- No em dashes anywhere. Write plain sentences.
- Keep third parties out of the dashboard: no CDN, no analytics, no fonts fetched from the network.
- A layer guide has the same shape as the others. Prefer a service an agent can sign itself up for, then a free local tool, and name any human step explicitly.
- Commit under your own name with no attribution trailers.
