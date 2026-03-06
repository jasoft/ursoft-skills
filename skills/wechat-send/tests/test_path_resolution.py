from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import wechat_auto


class PathResolutionTests(unittest.TestCase):
    def make_skill(self, root: Path) -> Path:
        scripts = root / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "gui").write_text("#!/bin/zsh\n", encoding="utf-8")
        (scripts / "ocr").write_text("#!/bin/zsh\n", encoding="utf-8")
        return root

    def test_prefers_explicit_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = self.make_skill(Path(tmpdir) / "localmac-ai-ocr")
            resolved = wechat_auto.resolve_localmac_ai_ocr_dir(str(skill_dir))
        self.assertEqual(resolved, skill_dir.resolve())

    def test_uses_env_var(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = self.make_skill(Path(tmpdir) / "localmac-ai-ocr")
            old = os.environ.get("LOCALMAC_AI_OCR_DIR")
            os.environ["LOCALMAC_AI_OCR_DIR"] = str(skill_dir)
            try:
                resolved = wechat_auto.resolve_localmac_ai_ocr_dir()
            finally:
                if old is None:
                    os.environ.pop("LOCALMAC_AI_OCR_DIR", None)
                else:
                    os.environ["LOCALMAC_AI_OCR_DIR"] = old
        self.assertEqual(resolved, skill_dir.resolve())

    def test_finds_repo_sibling_skill(self) -> None:
        resolved = wechat_auto.resolve_localmac_ai_ocr_dir()
        self.assertEqual(resolved, (ROOT.parent / "localmac-ai-ocr").resolve())


if __name__ == "__main__":
    unittest.main()
