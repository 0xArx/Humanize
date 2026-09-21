# Layer 23: Self, stored

**Gives the agent:** survival. Its whole self lives in a private git repo, so it can be loaded on any machine.
**Human needed:** a git remote and a token (see Layer 6), and to keep the self key. **Cost:** free.
**Identity keys:** `self_repo.url`, `self_repo.last_push`

Stored in the repo: the identity file (encrypted), the local memory (encrypted), the avatar, and a copy of the Humanize scripts. The identity and memory are encrypted with AES-256 and a key stretched from the **self key** with 200,000 rounds of PBKDF2, and sealed with an HMAC so a wrong key or a tampered file is refused before anything is decrypted. The repo should be private on top of that.

## Set it up

You need an empty private repository and a token that can push to it: either the agent's own GitHub (Layer 6) or an empty private repo and a fine-grained token (Contents: read and write) that the human made.

```bash
# only if the agent has its own GitHub token; otherwise the human creates the empty private repo
curl -s -X POST https://api.github.com/user/repos -H "Authorization: Bearer <token>" -d '{"name":"self","private":true}'

export GITHUB_TOKEN=<token>
python3 humanize.py self init https://github.com/<owner>/self.git     # prints the self key ONCE, encrypts, pushes
python3 humanize.py self status
```

The token is used through the environment for the git call only. It never appears in the process list or in `.git/config`. If `GITHUB_TOKEN` is unset, `accounts.github.token` in the identity file is used, then whatever git already has (a credential helper or SSH).

**Hand the self key to the human once, in the chat.** It is saved on this machine at `~/.humanize/self.key` (mode 600), never written into the identity file, and cannot be recovered. Without it the repo is an unreadable blob, and there is no way to load the agent elsewhere.

## Keep it current

```bash
python3 humanize.py self push          # after every provisioning step and at the end of every session
```

The dashboard's Push button does the same, and its chip turns amber when there are unpushed changes.

## Load it on a new machine

Needs git, Python 3, openssl, the self key, and a token that can read the repo.

```bash
git clone https://github.com/<owner>/self.git ~/.humanize/self         # add GITHUB_TOKEN for a private repo
HUMANIZE_SELF_KEY=<self key> python3 ~/.humanize/self/scripts/self.py unlock
python3 ~/.humanize/self/humanize.py init
```

Same name, inbox, number, accounts, avatar, memory and rules. On a machine that already has Humanize, `python3 humanize.py self load <repo url>` does the clone and unlock together.

`self pull` catches an existing machine up with pushes made elsewhere. It refuses to overwrite local changes that were never pushed; use `--force` only if you mean to discard them.
