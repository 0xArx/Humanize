# Layer 10: Computer

**Gives the agent:** a machine of its own for long jobs, servers and scheduled scripts, so it does not do them on the human's laptop.
**Human needed:** none for a local container; a card for a cloud machine. **Cost:** free locally.
**Identity keys:** `computer.provider`, `computer.id`, `ssh.public_key`

## An SSH key first

```bash
ssh-keygen -t ed25519 -N "" -C "<agent name>" -f ~/.humanize/ssh
python3 humanize.py set ssh.public_key "$(cat ~/.humanize/ssh.pub)"
```

Keep `~/.humanize/ssh` (the private half) out of the identity file; put it in the vault (Layer 13).

## Pick the first that applies

1. **A local container** if Docker is installed. No account.
   ```bash
   docker run -d --name <agent>-box --restart unless-stopped ubuntu:24.04 sleep infinity
   docker exec <agent>-box uname -a
   python3 humanize.py set computer.provider docker && python3 humanize.py set computer.id "<agent>-box"
   ```
2. **A GitHub Codespace** on the agent's own GitHub (Layer 6), through the `gh` CLI with a token that has the `codespace` scope. GitHub gives free personal accounts a monthly allowance of core hours; check the current amount before relying on it.
   ```bash
   gh codespace create --repo <agent>/<repo> --machine basicLinux32gb
   ```
3. **A cloud machine** (Hetzner, Fly.io, AWS). These need a payment card, which is a human step (Layer 4). Do it only for a task that truly needs an always-on machine.

> Status (2026-09-21): ssh-keygen tested here. The Docker and Codespaces commands are standard; not exercised.
