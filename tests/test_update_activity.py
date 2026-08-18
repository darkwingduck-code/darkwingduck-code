import unittest
from collections import Counter
from datetime import datetime, timezone

from scripts.update_activity import language_for, paginated, render_svg


class ActivitySummaryTests(unittest.TestCase):
    def test_generated_and_lock_files_are_excluded(self):
        self.assertIsNone(language_for("web/node_modules/pkg/index.js"))
        self.assertIsNone(language_for("package-lock.json"))
        self.assertEqual(language_for("src/app.tsx"), "TypeScript")

    def test_svg_contains_totals_rows_and_period(self):
        totals = Counter({"Python:additions": 1200, "Python:deletions": 34, "TypeScript:additions": 300, "TypeScript:deletions": 20})
        since = datetime(2026, 7, 19, tzinfo=timezone.utc)
        until = datetime(2026, 8, 18, tzinfo=timezone.utc)
        svg = render_svg(totals, since, until)
        self.assertIn("+1,500", svg)
        self.assertIn("−54", svg)
        self.assertIn("+1,200 / -34", svg)
        self.assertIn("2026-07-19 → 2026-08-18", svg)


    def test_empty_repository_conflict_is_skipped(self):
        from unittest.mock import patch
        from urllib.error import HTTPError

        conflict = HTTPError("https://api.github.com/repos/x/y/commits", 409, "Conflict", {}, None)
        with patch("scripts.update_activity.api", side_effect=conflict):
            self.assertEqual(paginated("/repos/x/y/commits", {}), [])

if __name__ == "__main__":
    unittest.main()
