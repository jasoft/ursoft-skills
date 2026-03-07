#!/usr/bin/env python3
"""Automate WeChat messaging on macOS."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
LOCALMAC_SKILL_NAME = "localmac-ai-ocr"
DEFAULT_CHAT_INPUT = ("400", "600")


def format_cmd(cmd: Sequence[object]) -> str:
    return " ".join(str(part) for part in cmd)


def run_process(
    cmd: Sequence[object], timeout: int = 30
) -> subprocess.CompletedProcess[str]:
    cmd_parts = [str(part) for part in cmd]
    try:
        return subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out: {format_cmd(cmd_parts)}") from exc


def run(cmd: Sequence[object], timeout: int = 30) -> str:
    result = run_process(cmd, timeout=timeout)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {format_cmd(cmd)}"
            + (f"\n{stderr}" if stderr else "")
        )
    return result.stdout.strip()


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def osascript(script: str, args: Optional[List[str]] = None) -> str:
    cmd: List[object] = ["osascript", "-e", script]
    if args:
        cmd.extend(args)
    return run(cmd)


def activate_wechat() -> None:
    script = """
tell application "WeChat" to activate
tell application "System Events"
    tell process "WeChat"
        set frontmost to true
    end tell
end tell
"""
    osascript(script)


def type_text_via_clipboard(text: str) -> None:
    result = subprocess.run(
        ["pbcopy"],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            "Failed to copy text to clipboard" + (f": {stderr}" if stderr else "")
        )

    script = """
tell application "System Events"
    keystroke "v" using command down
end tell
"""
    osascript(script)
    time.sleep(0.2)


def press_return() -> None:
    script = """
tell application "System Events"
    keystroke return
end tell
"""
    osascript(script)


def take_screenshot(save_path: str = "/tmp/wechat_screenshot.png") -> str:
    run(["/usr/sbin/screencapture", "-x", save_path])
    if not Path(save_path).exists():
        raise RuntimeError(f"Screenshot not created: {save_path}")
    return save_path


def find_text_in_ocr(
    ocr_results: List[dict], query: str, min_score: float = 0.9
) -> Optional[dict]:
    query_lower = query.lower()
    for item in ocr_results:
        text = item.get("text", "")
        score = item.get("score", 0.0)
        if score >= min_score and query_lower in text.lower():
            return item
    return None


def get_center_bbox(bbox: List[float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def has_localmac_scripts(root: Path) -> bool:
    return (root / "scripts" / "gui").is_file() and (root / "scripts" / "ocr").is_file()


def localmac_ai_ocr_candidates(explicit_dir: Optional[str] = None) -> List[Path]:
    candidates: List[Path] = []

    if explicit_dir:
        candidates.append(Path(explicit_dir).expanduser())

    env_dir = os.environ.get("LOCALMAC_AI_OCR_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())

    candidates.extend(
        [
            ROOT.parent / LOCALMAC_SKILL_NAME,
            Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
            / "skills"
            / LOCALMAC_SKILL_NAME,
            Path.home() / ".agents" / "skills" / LOCALMAC_SKILL_NAME,
            Path.home() / ".openclaw" / "skills" / LOCALMAC_SKILL_NAME,
        ]
    )

    deduped: List[Path] = []
    seen = set()
    for path in candidates:
        normalized = str(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(path)
    return deduped


def resolve_localmac_ai_ocr_dir(explicit_dir: Optional[str] = None) -> Path:
    for candidate in localmac_ai_ocr_candidates(explicit_dir):
        if has_localmac_scripts(candidate):
            return candidate.resolve()
    searched = ", ".join(str(path) for path in localmac_ai_ocr_candidates(explicit_dir))
    raise FileNotFoundError(
        "localmac-ai-ocr skill not found. Expected scripts/gui and scripts/ocr in one of: "
        f"{searched}"
    )


class LocalmacTools:
    def __init__(self, skill_dir: Optional[str] = None):
        self.root = resolve_localmac_ai_ocr_dir(skill_dir)
        self.gui = self.root / "scripts" / "gui"
        self.ocr = self.root / "scripts" / "ocr"

    def run_gui(self, *args: str, timeout: int = 30) -> str:
        return run([self.gui, *args], timeout=timeout)

    def run_ocr(self, *args: str, timeout: int = 30) -> str:
        return run([self.ocr, *args], timeout=timeout)


def ocr_image(
    image_path: str, backend: str = "auto", ocr_skill_dir: Optional[str] = None
) -> List[dict]:
    tools = LocalmacTools(ocr_skill_dir)
    cmd = ["ocr", image_path, "--format", "json"]
    if backend != "auto":
        cmd.extend(["--backend", backend])
    output = tools.run_ocr(*cmd)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OCR returned invalid JSON: {output[:200]}") from exc


class WeChatAuto:
    def __init__(
        self,
        debug: bool = False,
        delay: float = 0.5,
        ocr_backend: str = "auto",
        ocr_skill_dir: Optional[str] = None,
    ):
        self.debug = debug
        self.delay = delay
        self.ocr_backend = ocr_backend
        self.tools = LocalmacTools(ocr_skill_dir)

    def log(self, msg: str) -> None:
        if self.debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def run_gui(self, *args: str, timeout: int = 30) -> str:
        self.log(f"GUI command: {args}")
        return self.tools.run_gui(*args, timeout=timeout)

    def run_ocr(self, *args: str, timeout: int = 30) -> str:
        self.log(f"OCR command: {args}")
        return self.tools.run_ocr(*args, timeout=timeout)

    def wait_for_wechat(self, timeout: int = 10) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                script = """
tell application "System Events"
    return (name of first application process whose frontmost is true)
end tell
"""
                result = osascript(script)
                if "WeChat" in result:
                    return True
            except RuntimeError:
                pass
            time.sleep(0.5)
        return False

    def ensure_wechat_frontmost(self) -> None:
        activate_wechat()
        time.sleep(max(self.delay, 0.5))
        if not self.wait_for_wechat():
            raise RuntimeError("WeChat window did not become active")

    def ensure_wechat_running(self) -> None:
        result = run_process(["pgrep", "-x", "WeChat"])
        if result.returncode != 0:
            print("WeChat is not running, attempting to launch...")
            launch = run_process(["open", "-a", "WeChat"], timeout=15)
            if launch.returncode != 0:
                stderr = launch.stderr.strip()
                raise RuntimeError(
                    "Failed to launch WeChat" + (f": {stderr}" if stderr else "")
                )
            time.sleep(3.0)
        else:
            self.log("WeChat is already running")

        self.ensure_wechat_frontmost()

    def search_contact(self, contact_name: str) -> bool:
        self.log(f"Searching for contact: {contact_name}")

        script = """
tell application "System Events"
    keystroke "2" using command down
    keystroke "f" using command down
end tell
"""
        osascript(script)
        time.sleep(self.delay)

        clear_script = """
tell application "System Events"
    keystroke "a" using command down
    keystroke (ASCII character 8)
end tell
"""
        osascript(clear_script)
        time.sleep(0.3)

        type_text_via_clipboard(contact_name)
        time.sleep(1.0)
        press_return()
        time.sleep(self.delay)
        return True

    def send_message(self, contact_name: str, message: str) -> bool:
        self.log(f"Sending to {contact_name}: {message[:50]}")
        self.ensure_wechat_running()

        if not self.search_contact(contact_name):
            raise RuntimeError(f"Could not find contact: {contact_name}")

        self.ensure_wechat_frontmost()
        time.sleep(self.delay)

        type_text_via_clipboard(message)
        time.sleep(0.5)
        press_return()
        time.sleep(0.5)

        self.log("Message sent")
        return True


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str
    required: bool = True


def executable_check(path: Path, label: str) -> DoctorCheck:
    if not path.is_file():
        return DoctorCheck(label, False, f"Missing file: {path}")
    if not os.access(path, os.X_OK):
        return DoctorCheck(label, False, f"Not executable: {path}")
    return DoctorCheck(label, True, str(path))


def command_check(name: str) -> DoctorCheck:
    path = which(name)
    if path:
        return DoctorCheck(name, True, path)
    return DoctorCheck(name, False, f"Missing command: {name}")


def wechat_app_check() -> DoctorCheck:
    result = run_process(["open", "-Ra", "WeChat"], timeout=15)
    if result.returncode == 0:
        return DoctorCheck("WeChat.app", True, "WeChat is available")
    stderr = result.stderr.strip() or result.stdout.strip() or "WeChat not found"
    return DoctorCheck("WeChat.app", False, stderr)


def run_json_command(cmd: Sequence[object], timeout: int = 90) -> dict:
    result = run_process(cmd, timeout=timeout)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {format_cmd(cmd)}"
            + (f"\n{stderr}" if stderr else "")
        )
    output = result.stdout.strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Command returned invalid JSON: {format_cmd(cmd)}\n{output[:200]}"
        ) from exc


def downstream_doctor_checks(tools: LocalmacTools) -> Iterable[DoctorCheck]:
    gui_report = run_json_command([tools.gui, "doctor", "--json"])
    for key in ("uv", "osascript", "screencapture", "sips", "python3"):
        yield DoctorCheck(
            f"localmac gui:{key}",
            bool(gui_report.get(key)),
            f"{key}={gui_report.get(key)!r}",
        )

    ocr_report = run_json_command([tools.ocr, "doctor"])
    backend_ready = bool(
        ocr_report.get("aistudio_configured") or ocr_report.get("paddle_ready")
    )
    preferred_backend = ocr_report.get("preferred_backend")
    detail = (
        f"aistudio_configured={ocr_report.get('aistudio_configured')!r}, "
        f"paddle_ready={ocr_report.get('paddle_ready')!r}, "
        f"preferred_backend={preferred_backend!r}"
    )
    yield DoctorCheck("localmac ocr:backend", backend_ready, detail)


def collect_doctor_checks(
    explicit_ocr_skill_dir: Optional[str] = None,
) -> List[DoctorCheck]:
    checks = [
        command_check("python3"),
        command_check("osascript"),
        command_check("pbcopy"),
        command_check("pbpaste"),
        command_check("open"),
        command_check("pgrep"),
        wechat_app_check(),
    ]

    try:
        tools = LocalmacTools(explicit_ocr_skill_dir)
    except FileNotFoundError as exc:
        checks.append(DoctorCheck("localmac-ai-ocr", False, str(exc)))
        return checks

    checks.append(DoctorCheck("localmac-ai-ocr", True, str(tools.root)))
    checks.append(executable_check(tools.gui, "localmac gui script"))
    checks.append(executable_check(tools.ocr, "localmac ocr script"))
    checks.append(command_check("uv"))

    if all(check.ok for check in checks[-3:]):
        try:
            checks.extend(downstream_doctor_checks(tools))
        except RuntimeError as exc:
            checks.append(DoctorCheck("localmac doctor", False, str(exc)))

    return checks


def print_doctor_report(checks: Sequence[DoctorCheck]) -> None:
    for check in checks:
        status = "OK" if check.ok else "ERR"
        print(f"[{status}] {check.name}: {check.detail}")


def run_doctor(explicit_ocr_skill_dir: Optional[str] = None) -> int:
    checks = collect_doctor_checks(explicit_ocr_skill_dir)
    print_doctor_report(checks)
    failures = [check.name for check in checks if check.required and not check.ok]
    if failures:
        print(
            "Error: doctor found missing or invalid dependencies: "
            + ", ".join(failures),
            file=sys.stderr,
        )
        return 1
    print("doctor ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automate WeChat messaging on macOS")
    sub = parser.add_subparsers(dest="action", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--ocr-skill-dir",
        help="Path to the localmac-ai-ocr skill directory",
    )
    shared.add_argument("--debug", action="store_true", help="Enable debug output")

    send = sub.add_parser("send", parents=[shared], help="Send a message")
    send.add_argument("contact", help="Contact name to search for")
    send.add_argument("message", help="Message text to send")
    send.add_argument(
        "--delay", type=float, default=0.5, help="Delay between actions (seconds)"
    )
    send.add_argument(
        "--ocr-backend",
        default="auto",
        choices=["auto", "aistudio-ocr", "paddle"],
        help="OCR backend to use",
    )

    sub.add_parser("doctor", parents=[shared], help="Check required environment")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.action == "doctor":
            return run_doctor(explicit_ocr_skill_dir=args.ocr_skill_dir)

        wc = WeChatAuto(
            debug=args.debug,
            delay=args.delay,
            ocr_backend=args.ocr_backend,
            ocr_skill_dir=args.ocr_skill_dir,
        )
        wc.send_message(args.contact, args.message)
        print(f"Message sent to {args.contact}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
