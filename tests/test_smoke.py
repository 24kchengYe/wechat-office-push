from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fill_team_research_template as team  # noqa: E402
import fill_wechat_template as normal  # noqa: E402
import render_paper_article as renderer  # noqa: E402


class SkillSmokeTests(unittest.TestCase):
    def test_profiles_and_template_assets_resolve(self):
        for name in ("bcl", "tus"):
            profile = json.loads((ROOT / "profiles" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["profile_id"], name)
            config = profile.get("paper_template_config")
            if config:
                self.assertTrue((ROOT / config).is_file())

    def test_team_recommendation_uses_current_article(self):
        article = {
            "headline": "团队研究｜示例论文",
            "guide": [{"type": "paragraph", "text": "这是当前论文的研究概述，不应沿用历史论文内容。"}],
        }
        value = team.recommendation(article)
        self.assertIn("示例论文", value)
        self.assertNotIn("PREQ", value)
        self.assertLessEqual(normal.recommendation_count(value), 120)

    def test_team_author_affiliation_suffixes_are_removed(self):
        self.assertEqual(team.display_authors("Alicea, Bob*c"), "Alice, Bob*")

    def test_renderer_requires_local_editor_configuration(self):
        source = {
            "title_cn": "示例",
            "title_en": "Example",
            "doi": "10.0000/example",
            "authors": [{"name": "A"}],
            "image_files": [],
            "date": "2026年8月11日",
            "time": "12:00",
            "guide_cn": "概述。",
            "abstract_en": "Abstract.",
        }
        profile = {"account_name": "BCL", "show_editor": True, "default_editor": ""}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "responsible editor"):
                renderer.render(source, profile, Path(directory))


if __name__ == "__main__":
    unittest.main()
