# Layer 5: Browser

**Gives the agent:** hands, for any service that has no API.
**Human needed:** only to click through a CAPTCHA, if one appears. **Cost:** free.
**Identity keys:** `browser.provider`

Use the browser your host already gives you. Only install one if you have none.

1. **Claude Code:** the built-in Browser pane (`preview_start` with a `url`, then `read_page`, `find`, `computer`, `form_input`). For an already logged-in session use Claude in Chrome. For native apps use computer use.
2. **Codex:** its browser or computer tool.
3. **Cursor, Windsurf, Cline, OpenClaw, or any agent with a browser MCP** (Playwright MCP, Chrome DevTools MCP): use that.
4. **Nothing available:** run a local headless browser with Playwright. No account, no key.
   ```bash
   python3 -m venv ~/.humanize/pw && ~/.humanize/pw/bin/pip install playwright && ~/.humanize/pw/bin/playwright install chromium
   ```
   Then drive it from a short script. A headless browser is easy for sites to detect, so prefer an API when one exists.

Record the choice so the next run does not decide again:

```bash
python3 humanize.py set browser.provider "claude-browser"     # or codex, playwright-mcp, playwright-local
```

## Doing a sign-up with any browser

1. Open the sign-up URL.
2. Fill the form with the agent's name (Layer 0) and email (Layer 1). Use the agent's number (Layer 2) if a phone is asked for.
3. Submit, then switch to Layer 1 or 2 to fetch the code or link.
4. Return, finish verification, and go straight to the token page for that service.
5. Copy the token out of the page into the Mailgent vault (Layer 13), with a pointer in the identity file. Do not leave it only in the browser.

## When a page shows a CAPTCHA

The agent cannot pass one. Stop there, finish everything else, and send the human one message: the page URL, what is already filled in, and that the only thing left is the CAPTCHA. The agent continues from the next step once it is done. Batch these; see the handoff in SKILL.md.
