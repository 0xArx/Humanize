# Layer 12: Brain

**Gives the agent:** other models to call, for sub-agents, batch work, or anything that should not consume the host's context.
**Human needed:** none locally; a signup and possibly a top-up for hosted models. **Cost:** free locally.
**Identity keys:** `brain.<provider>` (a pointer to the vault entry, never the key)

The host model is the agent's mind. This layer is extra. In order:

1. **A local model with Ollama.** No account, no key, no cost.
   ```bash
   ollama pull llama3.2 && curl -s http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"Say hi","stream":false}'
   python3 humanize.py set brain.ollama "llama3.2"
   ```
2. **OpenRouter: one key for over 500 models** from 80 providers, which replaces a signup at each of them. You can log in with GitHub, Google or email, it has free models (with low rate limits), and credits can be bought with USDC (a 5% fee) as well as a card. Base URL `https://openrouter.ai/api/v1`, OpenAI-compatible. Store the key in the vault.
3. **Groq** for a fast free tier of open models: a key at console.groq.com, OpenAI-compatible at `https://api.groq.com/openai/v1`.

```bash
curl -s https://openrouter.ai/api/v1/chat/completions -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/llama-3.3-70b-instruct:free","messages":[{"role":"user","content":"Say hi"}]}'
python3 humanize.py set brain.openrouter "vault:openrouter"
```

> Status (2026-09-21): OpenRouter's aggregation, USDC top-up and login options are from its docs and public pages. Not exercised.
