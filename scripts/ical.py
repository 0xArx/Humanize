"""A local calendar, in the standard iCalendar format (RFC 5545), no account and no server.

One file, $HUMANIZE_HOME/calendar.ics, plain text, mode 600. Any real calendar app can import it, and
`self.py` backs it up encrypted along with everything else. For a link other people can book time on,
see Layer 15's Cal.com section; this module is for the agent's own private schedule.

  ical.py add <title> <start ISO> [--end ISO] [--location L] [--description D]
  ical.py list [--from ISO] [--to ISO]
  ical.py delete <uid>

Named ical.py, not calendar.py: Python's own standard library has a `calendar` module, and importing
this one under that name risks silently picking up the stdlib module instead whenever anything else
in the process has already imported it (as `urllib.request` does, transitively). ical.py sidesteps the
whole class of bug by never sharing the stdlib's name.
"""
import os
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402


def die(msg):
    sys.exit(msg.rstrip())


def path():
    return store.home() / "calendar.ics"


def _fold(line):
    """RFC 5545 requires lines no longer than 75 octets, continued with a leading space."""
    out, rest = [], line
    while len(rest.encode()) > 75:
        cut = 74
        while len(rest[:cut].encode()) > 74:
            cut -= 1
        out.append(rest[:cut])
        rest = " " + rest[cut:]
    out.append(rest)
    return "\r\n".join(out)


def _escape(text):
    return re.sub(r"([,;\\])", r"\\\1", text or "").replace("\n", "\\n")


def _unescape(text):
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) == "n" else m.group(1), text or "")


def _read_text():
    """Read the file exactly as written, with no newline translation (RFC 5545 lines are CRLF)."""
    p = path()
    if not p.exists():
        return ""
    with open(p, "r", newline="") as f:
        return f.read()


def _write_text(text):
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        f.write(text)
    os.chmod(p, 0o600)


def _dt(iso):
    """Accept 'YYYY-MM-DD' or a full ISO 8601 datetime; normalise to iCalendar's UTC form."""
    iso = iso.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        return iso.replace("-", "") + "T000000Z", True
    t = time.strptime(iso.replace("Z", "").split("+")[0].split(".")[0], "%Y-%m-%dT%H:%M:%S")
    return time.strftime("%Y%m%dT%H%M%SZ", t), False


def _event_blocks(text):
    """Each VEVENT as its raw (still-folded) text, in file order, alongside its parsed fields."""
    blocks = []
    for raw in re.findall(r"BEGIN:VEVENT\r?\n.*?END:VEVENT\r?\n?", text, re.S):
        unfolded = re.sub(r"\r?\n[ \t]", "", raw).replace("\r\n", "\n")
        fields = dict(re.findall(r"^([A-Z]+)(?:;[^:]*)?:(.*)$", unfolded, re.M))
        blocks.append((raw, fields))
    return blocks


def _read():
    return [fields for _, fields in _event_blocks(_read_text())]


def add(title, start, end=None, location=None, description=None, uid=None):
    if not title or not title.strip():
        raise ValueError("an event needs a title")
    dtstart, all_day = _dt(start)
    dtend, _ = _dt(end) if end else (dtstart, all_day)
    eid = uid or str(uuid.uuid4())
    now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    lines = ["BEGIN:VEVENT", f"UID:{eid}", f"DTSTAMP:{now}", f"DTSTART:{dtstart}", f"DTEND:{dtend}",
             f"SUMMARY:{_escape(title)}"]
    if location:
        lines.append(f"LOCATION:{_escape(location)}")
    if description:
        lines.append(f"DESCRIPTION:{_escape(description)}")
    lines.append("END:VEVENT")
    block = "\r\n".join(_fold(l) for l in lines) + "\r\n"
    text = _read_text()
    if not text:
        header = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Humanize//ical.py//EN\r\n"
        _write_text(header + block + "END:VCALENDAR\r\n")
    else:
        marker = "END:VCALENDAR"
        idx = text.rfind(marker)
        if idx == -1:
            raise ValueError(f"{path()} does not look like a valid calendar file")
        _write_text(text[:idx] + block + text[idx:])
    return eid


def list_events(frm=None, to=None):
    events = _read()
    out = []
    for e in events:
        if frm and e.get("DTSTART", "") < _dt(frm)[0]:
            continue
        if to and e.get("DTSTART", "") > _dt(to)[0]:
            continue
        out.append({"uid": e.get("UID"), "title": _unescape(e.get("SUMMARY", "")), "start": e.get("DTSTART"),
                    "end": e.get("DTEND"), "location": _unescape(e.get("LOCATION")) if e.get("LOCATION") else None,
                    "description": _unescape(e.get("DESCRIPTION")) if e.get("DESCRIPTION") else None})
    return sorted(out, key=lambda e: e["start"] or "")


def delete(uid):
    if not path().exists():
        raise ValueError("no calendar file yet")
    text = _read_text()
    matches = [raw for raw, fields in _event_blocks(text) if fields.get("UID") == uid]
    if not matches:
        raise ValueError(f"no event with UID {uid}")
    for raw in matches:
        text = text.replace(raw, "", 1)
    _write_text(text)
    return len(matches)


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("title")
    p.add_argument("start")
    p.add_argument("--end")
    p.add_argument("--location")
    p.add_argument("--description")
    p = sub.add_parser("list")
    p.add_argument("--from", dest="frm")
    p.add_argument("--to")
    p = sub.add_parser("delete")
    p.add_argument("uid")
    a = ap.parse_args()
    try:
        if a.cmd == "add":
            print(add(a.title, a.start, a.end, a.location, a.description))
        elif a.cmd == "list":
            print(json.dumps(list_events(a.frm, a.to), indent=2))
        elif a.cmd == "delete":
            delete(a.uid)
    except ValueError as e:
        die(str(e))


if __name__ == "__main__":
    main()
