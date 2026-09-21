# Layer 13: Keys and 2FA

**Gives the agent:** a place for every password, token and recovery code, and an authenticator that never blocks it.
**Human needed:** none. **Cost:** included with Mailgent.
**Identity keys:** `accounts.<service>.vault` (a pointer to the entry name, never the secret)

The Mailgent vault from Layer 1 is the store (encrypted at rest with AES-256-GCM) and it also produces one time codes.

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

The identity file keeps only a pointer, for example `accounts.github.vault = "github"`, so the file can be shown or shared without leaking anything.

> Status (2026-09-21): the vault commands and the `totp` and `totp-use-backup` commands are in the Mailgent CLI's source. The `--data` field name for a TOTP entry (`secret`) is not documented; if the first `vault totp` call errors, the error names the field it wants.
