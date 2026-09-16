# AGENTS.md

Instructions for AI coding agents and assistants working in or with this repository.

## What this repo is

A single skill, `humanize`, defined in `SKILL.md`. It teaches an AI model to write text that reads as human. There is no build step, no code, no tests. The deliverable is the markdown.

## How to use the skill

**Claude Code / Claude Agent SDK**
Copy or symlink this folder into your skills directory:

```bash
cp -r Humanize ~/.claude/skills/humanize
```

Then invoke with `/humanize` or just ask to humanize something. The `description` in the SKILL.md frontmatter handles automatic triggering.

**Cursor, Windsurf, Codex, Copilot, or any agent that reads AGENTS.md or rules files**
Paste the contents of `SKILL.md` into your rules file, system prompt, or `.cursorrules`. The skill is plain markdown and works as a system instruction on its own.

**Any chat model**
Paste `SKILL.md` at the top of the conversation, then paste the text you want humanized.

## Rules for agents editing this repo

- `SKILL.md` is the source of truth. Every other file describes or points to it.
- Keep the skill in one file. Do not split it into references unless it exceeds what a model can hold comfortably in context.
- The skill must follow its own rules. No em dashes anywhere in this repo. No banned words in the docs. If you add an example, the "after" version must pass the checklist at the bottom of `SKILL.md`.
- Do not add tooling, dependencies, package.json, or scripts. If you feel the need to, open an issue instead.
- Frontmatter `name` stays `humanize`. The `description` must remain a triggering description (what the skill does and when to use it), not marketing copy.
- When adding a tell, put it in the right category. Words go in the word list, patterns go under Tone or Content.
- Test changes by running the skill on the three examples in `SKILL.md` and on one new piece of text. If the output still sounds like a model, the change is not done.

## Commit style

Short, plain, imperative. "Add hedging tells." "Fix example two." No emoji, no conventional-commit prefixes required.
