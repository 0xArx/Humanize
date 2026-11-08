# Layer 13: Keys and 2FA

**Gives the agent:** a place for every password, token and recovery code, and an authenticator that never blocks it.
**Human needed:** none. **Cost:** free.
**Identity keys:** `accounts.<service>.vault` (a pointer to the entry name, never the secret)

Everything here is local. No vendor holds the vault, and no vendor generates the 2FA codes.

## The vault

The machine's own secret store, `scripts/keystore.py`: the macOS Keychain, the Linux keyring, or a private file where neither exists. It already holds any key that looks like a secret automatically; use it for anything else too, by name:

```bash
python3 humanize.py secret set accounts.github.password "<generated password>"
python3 humanize.py secret get accounts.github.password
python3 humanize.py secret list
python3 humanize.py secret delete accounts.github.password
```

Generate passwords with `openssl rand -base64 24`, one per service, never reused. Store recovery codes the same way, under a clear name like `accounts.github.recovery_codes`; they are the only way back in if a token is revoked.

## Two-factor codes, generated on this machine

When a service offers an authenticator app instead of only SMS, take the setup secret from its page (the `otpauth://` link's `secret` parameter, or the plain text alternative most sites show next to the QR code), store it, and generate codes locally:

```bash
python3 humanize.py totp new accounts.github.totp        # generates and stores a fresh secret, for setting up a NEW 2FA method
python3 humanize.py totp code accounts.github.totp        # the current 6-digit code and how long it is valid
```

This is `scripts/totp.py`: RFC 6238 over HMAC-SHA1, standard library only, checked against the official RFC 4226 test vectors in `tests/test_totp.py`. No account, no app to install, no vendor that could see the codes.

The identity file keeps only pointers, for example `accounts.github.vault = "accounts.github.password"`, so the file can be shown or shared without leaking anything. The encrypted backup carries the secret store's contents too, so loading the agent on a new machine restores them into that machine's store.

> Status (2026-09-22): the secret store commands are exercised by the test suite against the real macOS Keychain and a file fallback. The TOTP implementation matches all five RFC 6238 Appendix B test vectors and all ten RFC 4226 Appendix D test vectors exactly.
