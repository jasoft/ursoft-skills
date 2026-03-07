from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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

    def test_send_message_refocuses_wechat_before_paste(self) -> None:
        with mock.patch.object(
            wechat_auto, "LocalmacTools", autospec=True
        ) as tools_cls, mock.patch.object(
            wechat_auto.WeChatAuto, "ensure_wechat_running"
        ), mock.patch.object(
            wechat_auto.WeChatAuto, "search_contact", return_value=True
        ), mock.patch.object(
            wechat_auto.WeChatAuto, "ensure_wechat_frontmost"
        ) as ensure_frontmost, mock.patch.object(
            wechat_auto.WeChatAuto, "run_gui"
        ) as run_gui, mock.patch.object(
            wechat_auto, "type_text_via_clipboard"
        ) as paste_text, mock.patch.object(
            wechat_auto, "press_return"
        ):
            tools = tools_cls.return_value
            tools.root = Path("/tmp/localmac-ai-ocr")
            tools.gui = tools.root / "scripts" / "gui"
            tools.ocr = tools.root / "scripts" / "ocr"

            wc = wechat_auto.WeChatAuto()
            wc.send_message("文件传输助手", "测试消息")

        ensure_frontmost.assert_called()
        run_gui.assert_called_once_with("click", "400", "600")
        paste_text.assert_called_once_with("测试消息")

    def test_doctor_returns_nonzero_when_required_check_fails(self) -> None:
        checks = [wechat_auto.DoctorCheck("osascript", False, "missing")]
        with mock.patch.object(
            wechat_auto, "collect_doctor_checks", return_value=checks
        ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            exit_code = wechat_auto.run_doctor()
        self.assertEqual(exit_code, 1)

    def test_doctor_returns_zero_when_all_checks_pass(self) -> None:
        checks = [wechat_auto.DoctorCheck("osascript", True, "/usr/bin/osascript")]
        with mock.patch.object(
            wechat_auto, "collect_doctor_checks", return_value=checks
        ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            exit_code = wechat_auto.run_doctor()
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
