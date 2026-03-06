#!/usr/bin/env python3
"""
WeChat Auto - GUI Automation for WeChat on macOS using OCR assistance.
Requires localmac-ai-ocr skill to be installed and configured.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


# Locate localmac-ai-ocr tools
def find_ocr_tool() -> Optional[str]:
    """Find the ocr script from localmac-ai-ocr skill."""
    possible_paths = [
        Path("/Users/weiwang/.openclaw/skills/localmac-ai-ocr/scripts/ocr"),
        Path.home() / ".openclaw/skills/localmac-ai-ocr/scripts/ocr",
        Path("/Users/weiwang/.agents/skills/localmac-ai-ocr/scripts/ocr"),
    ]
    for p in possible_paths:
        if p.exists() and p.is_file():
            return str(p)
    return None


OCR_TOOL = find_ocr_tool()
if not OCR_TOOL:
    print(
        "Error: localmac-ai-ocr skill not found. Please install it first.",
        file=sys.stderr,
    )
    sys.exit(1)


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
    script = """
tell application "WeChat" to activate
tell application "System Events"
    tell process "WeChat"
        set frontmost to true
    end tell
end tell
"""
    try:
        osascript(script)
        time.sleep(1.0)  # Wait for window to become active
    except Exception as e:
        print(f"Warning: Failed to activate WeChat: {e}", file=sys.stderr)
        print("Make sure WeChat is installed and accessible.", file=sys.stderr)


def click_at(x: float, y: float) -> None:
    """Click at screen coordinates using macOS built-in tools."""
    # Use AppleScript to perform click
    script = f"""
tell application "System Events"
    click at {{{x}, {y}}}
end tell
"""
    try:
        osascript(script)
    except Exception as e:
        print(f"Warning: Click failed: {e}", file=sys.stderr)
        # Fallback: use cliclick if available
        try:
            run(["cliclick", "k:cmd", f"c:{int(x)},{int(y)}"])
        except:
            pass


def type_text_via_clipboard(text: str) -> None:
    """Copy text to clipboard and paste it (avoids input method)."""
    # Copy to clipboard using pbcopy
    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    p.communicate(input=text.encode("utf-8"))
    if p.returncode != 0:
        raise RuntimeError("Failed to copy to clipboard")

    # Paste using Cmd+V via AppleScript
    script = """
tell application "System Events"
    keystroke "v" using command down
end tell
"""
    osascript(script)
    time.sleep(0.2)


def press_return() -> None:
    """Press Return key."""
    script = """
tell application "System Events"
    keystroke return
end tell
"""
    osascript(script)


def take_screenshot(save_path: str = "/tmp/wechat_screenshot.png") -> str:
    """Take a screenshot and return the path."""
    # Try using screencapture first (fast)
    try:
        run(["/usr/sbin/screencapture", "-x", save_path])
        if Path(save_path).exists():
            return save_path
    except:
        pass

    # Fallback: use Python Quartz (requires pyobjc)
    try:
        # Use AppleScript to capture screen
        script = """
        set screenshot to (do shell script "screencapture -x -")
        return screenshot
        """
        # This is tricky, let's use a simpler approach: osascript with screencapture
        # Actually, just use screencapture and read file

        # If screencapture failed, try with permissions check
        raise RuntimeError(
            "Screenshot failed - ensure Screen Recording permission is granted"
        )
    except Exception as e:
        raise RuntimeError(
            f"Cannot take screenshot: {e}. Please grant Screen Recording permission to Terminal in System Settings > Privacy & Security > Screen Recording."
        )


def ocr_image(image_path: str, backend: str = "auto") -> List[dict]:
    """Run OCR on an image and return structured results."""
    cmd = [OCR_TOOL, "ocr", image_path, "--format", "json"]
    if backend != "auto":
        cmd.extend(["--backend", backend])
    output = run(cmd)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        raise RuntimeError(f"OCR returned invalid JSON: {output[:200]}")


def find_text_in_ocr(
    ocr_results: List[dict], query: str, min_score: float = 0.9
) -> Optional[dict]:
    """Find the first OCR result matching query text (exact or contains)."""
    query_lower = query.lower()
    for item in ocr_results:
        text = item.get("text", "")
        score = item.get("score", 0.0)
        if score >= min_score and (query_lower in text.lower()):
            return item
    return None


def get_center_bbox(bbox: List[float]) -> Tuple[float, float]:
    """Get center coordinates from bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


class WeChatAuto:
    def __init__(
        self, debug: bool = False, delay: float = 0.5, ocr_backend: str = "auto"
    ):
        self.debug = debug
        self.delay = delay
        self.ocr_backend = ocr_backend

    def log(self, msg: str) -> None:
        if self.debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def wait_for_wechat(self, timeout: int = 10) -> bool:
        """Wait until WeChat is running and active."""
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

    def search_contact(self, contact_name: str) -> bool:
        """Search for a contact using Cmd+F (no OCR needed)."""
        self.log(f"Searching for contact: {contact_name}")

        # Ensure WeChat is active and press Cmd+F to open search
        script = """
tell application "System Events"
    keystroke "2" using command down
    keystroke "f" using command down
end tell
"""
        osascript(script)
        time.sleep(self.delay)

        # Clear any existing text (Cmd+A then delete)
        script = """
tell application "System Events"
    keystroke "a" using command down
    keystroke (ASCII character 8)  -- backspace
end tell
"""
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

        # After search_contact, we should be in the chat window
        # Input field is typically at the bottom. Just click there and type.
        # Click on approximate input area (center-bottom of window)
        # WeChat input is usually around (400, 600) on a standard window
        time.sleep(self.delay)

        # Paste message
        type_text_via_clipboard(message)
        time.sleep(0.5)

        # Send (Return)
        press_return()
        time.sleep(0.5)

        self.log("Message sent")
        return True


def main():
    parser = argparse.ArgumentParser(description="Automate WeChat messaging on macOS")
    parser.add_argument("action", choices=["send"], help="Action to perform")
    parser.add_argument("contact", help="Contact name to search for")
    parser.add_argument("message", help="Message text to send")
    parser.add_argument(
        "--delay", type=float, default=0.5, help="Delay between actions (seconds)"
    )
    parser.add_argument(
        "--ocr-backend",
        default="auto",
        choices=["auto", "aistudio-ocr", "paddle"],
        help="OCR backend to use",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    try:
        wc = WeChatAuto(
            debug=args.debug, delay=args.delay, ocr_backend=args.ocr_backend
        )
        if args.action == "send":
            wc.send_message(args.contact, args.message)
            print(f"✓ Message sent to {args.contact}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
