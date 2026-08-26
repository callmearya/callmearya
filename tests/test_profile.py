from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class ProfileAssetTests(unittest.TestCase):
    def test_spidey_atlas_uses_v2_dimensions(self) -> None:
        with Image.open(ROOT / "assets" / "spidey-spritesheet.webp") as atlas:
            self.assertEqual((1536, 2288), atlas.size)

    def test_generated_svgs_are_valid_and_self_contained(self) -> None:
        for name in ("dark.svg", "light.svg"):
            path = ROOT / name
            tree = ET.parse(path)
            svg = tree.getroot()
            self.assertEqual("1180", svg.attrib["width"])
            self.assertEqual("586", svg.attrib["height"])

            content = path.read_text(encoding="utf-8")
            self.assertIn("arya@callmearya", content)
            self.assertIn("Tech Enthusiast", content)
            self.assertIn('id="spidey"', content)
            self.assertIn("animateTransform", content)
            self.assertEqual(12, content.count("data:image/png;base64,"))
            self.assertNotIn("always exploring", content)

    def test_readme_targets_profile_repository(self) -> None:
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("pratikforge", content.lower())
        self.assertIn("raw.githubusercontent.com/callmearya/callmearya/main/dark.svg", content)
        self.assertIn("raw.githubusercontent.com/callmearya/callmearya/main/light.svg", content)
        self.assertIn("github-jet.svg", content)
        self.assertEqual([], re.findall(r"TODO|TBD|PLACEHOLDER", content, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
