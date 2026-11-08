# Layer 15: Calendar

**Gives the agent:** a calendar, and a page others can book time on.
**Human needed:** none. **Cost:** free.
**Identity keys:** `calendar.local`, `calendar.booking_url`

## Its own calendar

One local file, `~/.humanize/calendar.ics`, in the standard iCalendar format (RFC 5545) that every real calendar app can import. No account, no server.

```bash
python3 humanize.py calendar add "Call with Sana" 2026-09-24T15:00:00Z --end 2026-09-24T15:30:00Z --location "Zoom"
python3 humanize.py calendar list --from 2026-09-24 --to 2026-09-28
python3 humanize.py calendar delete <uid>
```

This is `scripts/ical.py`: standard library only, and `self.py` backs it up encrypted along with everything else (Layer 23).

## A public booking page

For a link other people can book time on, sign up at cal.com with the agent's email (the code arrives in its inbox) and create a 15 minute event type. That gives a link such as `https://cal.com/<handle>/15min`. Put it in email signatures and profiles.

```bash
python3 humanize.py set calendar.booking_url "https://cal.com/<handle>/15min"
```

A Google account is only worth the effort if a task needs Google Calendar specifically; its sign-up asks for a phone and often a CAPTCHA.

> Status (2026-09-22): `ical.py`'s ICS output was checked for balanced VEVENT blocks, line folding and correct all-day and timed dates in `tests/test_calendar.py`. Cal.com sign-up was not exercised.
