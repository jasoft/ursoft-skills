#!/usr/bin/env python3
"""WeChat GUI automation on macOS with optional localmac-ai-ocr integration."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional


def resolve_localmac_ai_ocr_dir(explicit_dir: Optional[str] = None) -> Optional[Path]:
    """Locate the localmac-ai-ocr skill by env var, sibling path, or common install dirs."""
    candidates: list[Path] = []
    if explicit_dir:
        candidates.append(Path(explicit_dir).expanduser())

    env_dir = os.environ.get("LOCALMAC_AI_OCR_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    candidates.extend(
        [
            skill_root.parent / "localmac-ai-ocr",
            Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills" / "localmac-ai-ocr",
            Path.home() / ".agents" / "skills" / "localmac-ai-ocr",
        ]
    )

    seen: set[Path] = set()
    for candidate in candidates:
        root = candidate.resolve()
        if root in seen:
            continue
        seen.add(root)
        if (root / "scripts" / "ocr").is_file() and (root / "scripts" / "gui").is_file():
            return root
    return None


class LocalmacTools:
    """Thin wrapper around the public CLI surface of localmac-ai-ocr."""

    def __init__(self, skill_dir: Optional[str] = None):
        root = resolve_localmac_ai_ocr_dir(skill_dir)
        if root is None:
            raise RuntimeError(
                "找不到 localmac-ai-ocr。请设置 LOCALMAC_AI_OCR_DIR，"
                "或把它放在当前 skill 的同级目录、$CODEX_HOME/skills、$HOME/.agents/skills 之一。"
            )
        self.root = root
        self.gui = root / "scripts" / "gui"
        self.ocr = root / "scripts" / "ocr"


def run(cmd: List[str], timeout: int = 30) -> str:
    """Run a command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out: {' '.join(cmd)}")

def osascript(script: str, args: Optional[List[str]] = None) -> str:
    """Run an AppleScript via osascript."""
    cmd = ["osascript", "-e", script]
    if args:
        cmd.extend(args)
    return run(cmd)

def activate_wechat() -> None:
    """Activate WeChat application and bring to foreground."""
    script = '''
tell application "WeChat" to activate
tell application "System Events"
    tell process "WeChat"
        set frontmost to true
    end tell
end tell
'''
    try:
        osascript(script)
        time.sleep(1.0)  # Wait for window to become active
    except Exception as e:
        print(f"Warning: Failed to activate WeChat: {e}", file=sys.stderr)
        print("Make sure WeChat is installed and accessible.", file=sys.stderr)

def type_text_via_clipboard(text: str) -> None:
    """Copy text to clipboard and paste it (avoids input method)."""
    # Copy to clipboard using pbcopy
    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    p.communicate(input=text.encode("utf-8"))
    if p.returncode != 0:
        raise RuntimeError("Failed to copy to clipboard")

    # Paste using Cmd+V via AppleScript
    script = '''
tell application "System Events"
    keystroke "v" using command down
end tell
'''
    osascript(script)
    time.sleep(0.2)

def press_return() -> None:
    """Press Return key."""
    script = '''
tell application "System Events"
    keystroke return
end tell
'''
    osascript(script)


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

    def wait_for_wechat(self, timeout: int = 10) -> bool:
        """Wait until WeChat is running and active."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                script = '''
tell application "System Events"
    return (name of first application process whose frontmost is true)
end tell
'''
                result = osascript(script)
                if "WeChat" in result:
                    return True
            except:
                pass
            time.sleep(0.5)
        return False

    def ensure_wechat_running(self) -> None:
        """Check if WeChat is running, try to launch if not."""
        try:
            run(["pgrep", "-x", "WeChat"])
            self.log("WeChat is running")
        except:
            print("WeChat is not running, attempting to launch...")
            try:
                run(["open", "-a", "WeChat"])
                time.sleep(3.0)  # Wait for app to start
            except Exception as e:
                raise RuntimeError(f"Failed to launch WeChat: {e}")

        activate_wechat()
        if not self.wait_for_wechat():
            raise RuntimeError("WeChat window did not become active")

    def run_gui(self, *args: str) -> str:
        return run([str(self.tools.gui), *args])

    def search_contact(self, contact_name: str) -> bool:
        """Search for a contact using Cmd+F (no OCR needed)."""
        self.log(f"Searching for contact: {contact_name}")

        # Ensure WeChat is active and press Cmd+F to open search
        script = '''
tell application "System Events"
    keystroke "2" using command down
    keystroke "f" using command down
end tell
'''
        osascript(script)
        time.sleep(self.delay)

        # Clear any existing text (Cmd+A then delete)
        script = '''
tell application "System Events"
    keystroke "a" using command down
    keystroke (ASCII character 8)  -- backspace
end tell
'''
        osascript(script)
        time.sleep(0.3)

        # Paste contact name via clipboard
        type_text_via_clipboard(contact_name)
        time.sleep(1.0)  # Wait for search results to populate

        # Press Return to select first result
        press_return()
        time.sleep(self.delay)
        return True

    def send_message(self, contact_name: str, message: str) -> bool:
        """Send a message to a contact."""
        self.log(f"Sending to {contact_name}: {message[:50]}...")
        self.ensure_wechat_running()

        # Search for contact
        if not self.search_contact(contact_name):
            raise RuntimeError(f"Could not find contact: {contact_name}")

        # Prefer the shared GUI helper so clicking stays aligned with the OCR skill contract.
        self.run_gui("click", "400", "600")
        time.sleep(self.delay)

        # Paste message
        type_text_via_clipboard(message)
        time.sleep(0.5)

        # Send (Return)
        press_return()
        time.sleep(0.5)

        self.log("Message sent")
        return True

    def doctor(self) -> dict:
        """Return dependency and environment status as JSON-serializable data."""
        checks = {
            "wechat_app": True,
            "localmac_ai_ocr_dir": str(self.tools.root),
            "gui_script": str(self.tools.gui),
            "ocr_script": str(self.tools.ocr),
            "osascript": True,
            "pbcopy": True,
            "pbpaste": True,
        }
        for binary in ("osascript", "pbcopy", "pbpaste"):
            checks[binary] = subprocess.run(
                ["which", binary], capture_output=True, text=True
            ).returncode == 0
        checks["wechat_app"] = subprocess.run(
            ["mdfind", "kMDItemCFBundleIdentifier == 'com.tencent.xinWeChat'"],
            capture_output=True,
            text=True,
        ).returncode == 0
        return checks

def main():
    parser = argparse.ArgumentParser(description="Automate WeChat messaging on macOS")
    parser.add_argument("action", choices=["send", "doctor"], help="Action to perform")
    parser.add_argument("contact", nargs="?", help="Contact name to search for")
    parser.add_argument("message", nargs="?", help="Message text to send")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between actions (seconds)")
    parser.add_argument("--ocr-backend", default="auto", choices=["auto", "aistudio-ocr", "paddle"],
                        help="OCR backend to use")
    parser.add_argument("--ocr-skill-dir", help="Path to the localmac-ai-ocr skill root")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    try:
        wc = WeChatAuto(
            debug=args.debug,
            delay=args.delay,
            ocr_backend=args.ocr_backend,
            ocr_skill_dir=args.ocr_skill_dir,
        )
        if args.action == "doctor":
            print(json.dumps(wc.doctor(), ensure_ascii=False, indent=2))
            return
        if args.action == "send":
            if not args.contact or not args.message:
                raise RuntimeError("send 动作需要 contact 和 message 两个参数")
            wc.send_message(args.contact, args.message)
            print(f"✓ Message sent to {args.contact}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
