# Layer 13: Keys and 2FA

**Gives the agent:** a place for every password, token and recovery code, and an authenticator that never blocks it.
**Human needed:** none. **Cost:** included with Mailgent.
**Identity keys:** `accounts.<service>.vault` (a pointer to the entry name, never the secret)

There are two places, and each secret has exactly one:

- **The Mailgent vault** holds passwords, 2FA secrets, recovery codes, account tokens and extra wallet keys. It is encrypted at rest with AES-256-GCM and it also produces one time codes.
- **The machine's secret store** (the macOS Keychain, the Linux keyring, or a private file where neither exists) holds the few keys the agent needs to reach the vault and its own services: the Mailgent, AgentMail and AgentPhone API keys, and the self key. `python3 humanize.py set <path> <value>` puts a secret-looking key there automatically and leaves only a pointer in the identity file; `python3 humanize.py get <path>` fetches it. Use `secret list` to see what is stored.

```bash
# any credential
mailgent vault store github --type LOGIN --data '{"username":"<u>","password":"<p>"}'
mailgent vault store-api-key stripe --secret sk_test_...
mailgent vault get github --json
mailgent vault list

# a 2FA secret is its own entry of type TOTP
mailgent vault store github-2fa --type TOTP --data '{"secret":"<base32 secret from the QR page>"}'
mailgent vault totp github-2fa               # prints the current 6 digit code and how long it lasts
mailgent vault totp-use-backup github-2fa    # spends one single-use backup code
```

Credential types are `LOGIN`, `API_KEY`, `OAUTH`, `TOTP`, `SSH_KEY`, `DATABASE`, `SMTP`, `AWS`, `CERTIFICATE`, `CARD`, `SHIPPING_ADDRESS` and `CUSTOM`.

When a service offers an authenticator app, take the setup secret from its page (the `otpauth://` link or the plain secret), store it as a `TOTP` entry, and generate codes with `vault totp`. Store the recovery codes in the same entry's backup codes if the type supports it, otherwise as a `CUSTOM` entry. They are the only way back in if a token is revoked.

Generate passwords with `openssl rand -base64 24`, one per service, never reused.

The identity file keeps only pointers, for example `accounts.github.vault = "github"` or `secret:email.mailgent.api_key`, so the file can be shown or shared without leaking anything. The encrypted backup carries the secret store's contents too, so loading the agent on a new machine restores them into that machine's store.

> Status (2026-09-21): the vault commands and the `totp` and `totp-use-backup` commands are in the Mailgent CLI's source. The `--data` field name for a TOTP entry (`secret`) is not documented; if the first `vault totp` call errors, the error names the field it wants.
