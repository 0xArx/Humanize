"""A local calendar in plain iCalendar (RFC 5545), no account and no server."""
import json
import re
import sys
import unittest

from helpers import HomeCase, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import ical as local_calendar  # noqa: E402


class ModuleTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_add_creates_the_file_at_mode_600_with_a_valid_header_and_footer(self):
        local_calendar.add("Standup", "2027-01-05T09:00:00")
        p = local_calendar.path()
        self.assertTrue(p.exists())
        self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
        with open(p, newline="") as f:
            text = f.read()
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        self.assertTrue(text.rstrip("\r\n").endswith("END:VCALENDAR"))
        self.assertEqual(text.count("BEGIN:VEVENT"), text.count("END:VEVENT"))

    def test_add_returns_a_uid_that_list_and_delete_can_use(self):
        uid = local_calendar.add("Dentist", "2027-02-01T10:00:00", location="Clinic", description="checkup")
        events = local_calendar.list_events()
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["uid"], uid)
        self.assertEqual(e["title"], "Dentist")
        self.assertEqual(e["location"], "Clinic")
        self.assertEqual(e["description"], "checkup")
        self.assertEqual(local_calendar.delete(uid), 1)
        self.assertEqual(local_calendar.list_events(), [])

    def test_a_second_event_is_appended_not_overwritten(self):
        local_calendar.add("First", "2027-01-01T09:00:00")
        local_calendar.add("Second", "2027-01-02T09:00:00")
        text = local_calendar.path().read_text()
        self.assertEqual(text.count("BEGIN:VEVENT"), 2)
        titles = {e["title"] for e in local_calendar.list_events()}
        self.assertEqual(titles, {"First", "Second"})

    def test_list_is_sorted_and_filters_by_date_range(self):
        local_calendar.add("Jan", "2027-01-15T09:00:00")
        local_calendar.add("Mar", "2027-03-15T09:00:00")
        local_calendar.add("Feb", "2027-02-15T09:00:00")
        self.assertEqual([e["title"] for e in local_calendar.list_events()], ["Jan", "Feb", "Mar"])
        in_range = local_calendar.list_events(frm="2027-02-01", to="2027-02-28")
        self.assertEqual([e["title"] for e in in_range], ["Feb"])

    def test_an_all_day_event_defaults_dtend_to_dtstart(self):
        uid = local_calendar.add("Holiday", "2027-04-01")
        e = local_calendar.list_events()[0]
        self.assertEqual(e["start"], "20270401T000000Z")
        self.assertEqual(e["end"], "20270401T000000Z")
        local_calendar.delete(uid)

    def test_title_with_special_characters_is_escaped_and_round_trips(self):
        local_calendar.add("Comma, semi; back\\slash", "2027-05-01T09:00:00")
        e = local_calendar.list_events()[0]
        self.assertEqual(e["title"], "Comma, semi; back\\slash")

    def test_a_very_long_title_is_line_folded_and_still_round_trips(self):
        long_title = "Quarterly planning review with the whole team " * 3
        local_calendar.add(long_title.strip(), "2027-06-01T09:00:00")
        with open(local_calendar.path(), newline="") as f:
            text = f.read()
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode()), 75, f"unfolded line too long: {line!r}")
        e = local_calendar.list_events()[0]
        self.assertEqual(e["title"], long_title.strip())

    def test_an_empty_title_is_rejected(self):
        with self.assertRaises(ValueError):
            local_calendar.add("", "2027-01-01T09:00:00")
        with self.assertRaises(ValueError):
            local_calendar.add("   ", "2027-01-01T09:00:00")

    def test_deleting_an_unknown_uid_is_a_clear_error(self):
        local_calendar.add("Something", "2027-01-01T09:00:00")
        with self.assertRaises(ValueError):
            local_calendar.delete("not-a-real-uid")

    def test_deleting_before_any_event_exists_is_a_clear_error(self):
        with self.assertRaises(ValueError):
            local_calendar.delete("anything")

    def test_deleting_one_event_leaves_the_others_intact(self):
        a = local_calendar.add("Keep me", "2027-01-01T09:00:00")
        b = local_calendar.add("Remove me", "2027-01-02T09:00:00")
        local_calendar.delete(b)
        remaining = local_calendar.list_events()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["uid"], a)


class CliTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_add_list_delete_round_trip(self):
        uid = self.hz("calendar", "add", "Team sync", "2027-01-05T09:00:00").stdout.strip()
        self.assertTrue(re.fullmatch(r"[0-9a-f-]{36}", uid))
        events = json.loads(self.hz("calendar", "list").stdout)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["uid"], uid)
        r = self.hz("calendar", "delete", uid)
        self.assertEqual(r.stdout.strip(), "")
        self.assertEqual(json.loads(self.hz("calendar", "list").stdout), [])

    def test_add_records_the_calendar_path_in_the_identity_once(self):
        self.hz("calendar", "add", "Something", "2027-01-05T09:00:00")
        d = self.load()
        self.assertEqual(d["calendar"]["local"], str(local_calendar.path()))

    def test_add_with_optional_fields(self):
        self.hz("calendar", "add", "Checkup", "2027-02-01T10:00:00", "--location", "Clinic", "--description", "annual")
        e = json.loads(self.hz("calendar", "list").stdout)[0]
        self.assertEqual(e["location"], "Clinic")
        self.assertEqual(e["description"], "annual")

    def test_list_can_be_filtered_by_from_and_to(self):
        self.hz("calendar", "add", "Jan", "2027-01-15T09:00:00")
        self.hz("calendar", "add", "Mar", "2027-03-15T09:00:00")
        events = json.loads(self.hz("calendar", "list", "--from", "2027-02-01", "--to", "2027-12-31").stdout)
        self.assertEqual([e["title"] for e in events], ["Mar"])

    def test_deleting_an_unknown_uid_fails_clearly(self):
        self.hz("calendar", "add", "Something", "2027-01-01T09:00:00")
        r = self.hz("calendar", "delete", "not-a-real-uid", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no event", r.stderr.lower())

    def test_an_empty_title_fails_clearly(self):
        r = self.hz("calendar", "add", "", "2027-01-01T09:00:00", check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
