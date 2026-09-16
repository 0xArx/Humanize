# Humanize

A skill that makes AI-written text sound like a person wrote it.

Models have habits. Em dashes, lists of three, "delve", "it's not just X, it's Y", a cheerful opener and a tidy recap at the end. Readers spot these in seconds. This skill lists the habits and tells the model how to write without them.

## What's in here

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill itself. Workflow, full list of tells, default voice, examples, checklist. |
| `AGENTS.md` | How to install it in Claude Code, Cursor, Codex, or any agent, plus rules for editing this repo. |
| `README.md` | This file. |

## Install

**Claude Code**

```bash
git clone https://github.com/0xArx/Humanize.git ~/.claude/skills/humanize
```

Then type `/humanize` followed by your text, or just ask Claude to make something sound human. It triggers on its own for emails, posts, and copy.

**Everything else**

Open `SKILL.md`, copy it, paste it into your system prompt or rules file. It is plain markdown and needs nothing else.

## What it does

1. Reads the text and figures out who it is for.
2. Matches your voice if you give it samples. Falls back to a plain, direct default if you don't.
3. Removes every AI tell on the list. Not softened, removed.
4. Fixes the rhythm so sentences don't all sound the same.
5. Adds one concrete detail or opinion so the writing comes from somewhere.
6. Returns the text, usually shorter than what went in.

## Example

Before:

> In today's fast-paced digital landscape, it's crucial to leverage cutting-edge tools that not only streamline your workflow but also empower your team to unlock their full potential.

After:

> Most teams waste time on tools that don't fit how they actually work. Here's what has worked for us.

## Matching your own voice

Give it a few of your real emails or posts. It copies your sentence length, your punctuation, your sign-off, and your quirks. It won't fix your grammar. That's the point.

## Contributing

Found a tell that isn't on the list? Add it to the right section in `SKILL.md` and send a pull request. Keep the repo free of the things the skill bans. Read `AGENTS.md` first.

## License

MIT
