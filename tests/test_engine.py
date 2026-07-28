#!/usr/bin/env python3
"""Tests for timeglass-last30days engine (stdlib unittest)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "timeglass-last30days"
SCRIPTS = SKILL / "scripts"
FIXTURE = SKILL / "fixtures" / "sample_month.json"
sys.path.insert(0, str(SCRIPTS))

from lib.parse import bundle_from_fixture, extract_team_ids, try_parse_json  # noqa: E402
from lib.render import render_html, render_markdown  # noqa: E402
from lib.stats import compute_stats  # noqa: E402


class FixtureTests(unittest.TestCase):
    def test_fixture_exists(self):
        self.assertTrue(FIXTURE.is_file())

    def test_bundle_totals(self):
        data = json.loads(FIXTURE.read_text())
        bundle = bundle_from_fixture(data)
        self.assertGreater(bundle.total_minutes, 0)
        self.assertTrue(bundle.projects)
        self.assertTrue(bundle.days)
        stats = compute_stats(bundle)
        self.assertEqual(stats.total_minutes, bundle.total_minutes)
        self.assertTrue(stats.top_projects)
        self.assertTrue(stats.identity_cards)
        md = render_markdown(stats)
        self.assertIn("timeglass-last30days", md)
        self.assertIn("Top projects", md)
        html = render_html(stats)
        self.assertIn("Work Wrapped", html)
        self.assertIn("top_projects", html)


class ParseHelpers(unittest.TestCase):
    def test_try_parse_json_fence(self):
        raw = "Here you go:\n```json\n{\"a\": 1}\n```\n"
        self.assertEqual(try_parse_json(raw), {"a": 1})

    def test_extract_team_ids_ignores_workspace(self):
        payload = {
            "workspaces": [
                {
                    "workspace_id": "ws-1",
                    "name": "Studio",
                    "team_tree": [{"team_id": "team-9", "name": "Core", "children": []}],
                }
            ]
        }
        teams = extract_team_ids(json.dumps(payload))
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]["team_id"], "team-9")


class CliTests(unittest.TestCase):
    def test_demo_compact(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "last30work.py"), "--demo", "--emit", "compact"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("timeglass-last30days", proc.stdout)
        self.assertIn("Top projects", proc.stdout)

    def test_demo_all_writes(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "last30work.py"),
                    "--demo",
                    "--emit",
                    "all",
                    "--out",
                    td,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = Path(td)
            self.assertTrue((out / "work-wrapped.json").is_file())
            self.assertTrue((out / "work-wrapped.md").is_file())
            self.assertTrue((out / "work-wrapped.html").is_file())
            html = (out / "work-wrapped.html").read_text()
            self.assertIn("<!DOCTYPE html>", html)

    def test_preflight(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "last30work.py"), "--preflight"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("scraping:  never", proc.stdout)


if __name__ == "__main__":
    unittest.main()
