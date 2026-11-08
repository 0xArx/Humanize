"""Ready-made profiles: valid files, and init --profile fills a new identity from one."""
import json
import unittest

from helpers import HomeCase, ROOT

PROFILES = sorted((ROOT / "profiles").glob("*.json"))
CORE = {0, 1, 7, 11, 13, 22, 23}


class ProfileFileTests(unittest.TestCase):
    def test_there_are_profiles(self):
        self.assertGreaterEqual(len(PROFILES), 5)

    def test_every_profile_is_complete_and_sane(self):
        for f in PROFILES:
            with self.subTest(profile=f.name):
                p = json.loads(f.read_text())
                self.assertEqual(p["id"], f.stem, "id must match the file name")
                for k in ("label", "summary", "name", "persona"):
                    self.assertTrue(p[k].strip(), k)
                self.assertTrue(p["business_card"]["title"] and p["business_card"]["tagline"])
                layers = set(p["layers"])
                self.assertTrue(all(0 <= n < 24 for n in layers), layers)
                self.assertTrue(CORE <= layers, f"missing core layers {CORE - layers}")
                self.assertTrue(any("spend cap" in r.lower() for r in p["rules"]), "every profile caps spending")


class InitProfileTests(HomeCase):
    def test_init_with_a_profile_fills_the_identity(self):
        r = self.hz("init", "--profile", "sales", "--port", "0", "--no-open")
        self.assertIn("Sales and outreach", r.stdout)
        d = self.load()
        p = json.loads((ROOT / "profiles" / "sales.json").read_text())
        self.assertEqual(d["name"], p["name"])
        self.assertEqual(d["persona"], p["persona"])
        self.assertEqual(d["profile"], "sales")
        self.assertEqual(d["rules"], p["rules"])
        self.assertEqual(d["business_card"]["title"], p["business_card"]["title"])
        on = {int(n) for n, v in d["layers"].items() if v["enabled"]}
        self.assertEqual(on, set(p["layers"]))
        self.assertEqual(len(d["layers"]), 24)

    def test_name_and_persona_flags_win_over_the_profile(self):
        self.hz("init", "--profile", "support", "--name", "Kit Okafor", "--persona", "Mine.", "--port", "0", "--no-open")
        d = self.load()
        self.assertEqual((d["name"], d["persona"], d["profile"]), ("Kit Okafor", "Mine.", "support"))

    def test_an_unknown_profile_fails_and_lists_the_choices(self):
        r = self.hz("init", "--profile", "nope", "--port", "0", "--no-open", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("assistant", r.stdout + r.stderr)
        self.assertFalse(self.identity.exists())

    def test_a_profile_never_overwrites_an_existing_identity(self):
        self.init("First Name")
        r = self.hz("init", "--profile", "builder", "--port", "0", "--no-open")
        self.assertIn("profile not applied", r.stdout)
        self.assertEqual(self.load()["name"], "First Name")

    def test_profiles_command_lists_every_profile(self):
        out = self.hz("profiles").stdout
        for f in PROFILES:
            self.assertIn(f.stem, out)


if __name__ == "__main__":
    unittest.main()
