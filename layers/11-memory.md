# Layer 11: Memory

**Gives the agent:** notes it can search and a list of people it has met, that survive across sessions.
**Human needed:** none. **Cost:** free.
**Identity keys:** `memory.local`

The default is one local SQLite file, `~/.humanize/memory.db` (mode 600), with full-text search. No account, no server. `humanize.py self push` backs it up, encrypted, next to the identity, so `self load` restores it on a new machine.

```bash
python3 humanize.py memory add "Met Sana Okafor at the KL conference; prefers WhatsApp" --kind person --tags "sana,conference"
python3 humanize.py memory search "sana conference"          # JSON list, best match first
python3 humanize.py memory person "Sana Okafor" --handle "@sana" --notes "KL conference"
python3 humanize.py memory people
```

Read memory at the start of a task and write to it at the end. Put contacts in `person`, everything else in `add` with a `--kind` such as `note`, `decision`, `fact` or `lesson`.

**Optional, remote:** if the agent needs semantic search over many documents, create a Supabase project (Layer 6) with a `memories` table and pgvector, and record the project ref under `memory.supabase`. Most agents never need this.
