# Layer 15: Calendar

**Gives the agent:** a calendar, and a page others can book time on.
**Human needed:** none. **Cost:** free.
**Identity keys:** `calendar.booking_url`

## The calendar it already has

The Mailgent sign-up (Layer 1) included one. The command line tool manages it:

```bash
mailgent calendar list --from 2026-09-21 --to 2026-09-28 --json
mailgent calendar create --title "Call with Sana" --start 2026-09-24T15:00:00Z --end 2026-09-24T15:30:00Z --location "Zoom"
mailgent calendar update <eventId> --start 2026-09-24T16:00:00Z
mailgent calendar get <eventId> --json
```

## A public booking page

Sign up at cal.com with the agent's email (the code arrives in its inbox) and create a 15 minute event type. That gives a link such as `https://cal.com/<handle>/15min`. Put it in email signatures and profiles.

```bash
python3 humanize.py set calendar.booking_url "https://cal.com/<handle>/15min"
```

A Google account is only worth the effort if a task needs Google Calendar specifically; its sign-up asks for a phone and often a CAPTCHA.

> Status (2026-09-21): the `mailgent calendar` commands are in the CLI's source. Cal.com sign-up not exercised.
