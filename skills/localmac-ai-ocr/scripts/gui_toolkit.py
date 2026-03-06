#!/usr/bin/env python3
"""
Minimal GUI automation toolkit for macOS-hosted RDP workflows.

This script avoids compile-time dependencies so it can work even when Xcode
license/toolchain setup is incomplete. It shells out to built-in macOS tools
for window activation and screenshots, and uses Quartz events via ctypes for
mouse input.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import ctypes
import io
import json
import os
import shlex
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=r"urllib3 .* doesn't match a supported version!",
)
import requests

APPLICATION_SERVICES = (
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)
TESSDATA_PREFIX = "/opt/homebrew/share/tessdata"


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


core_graphics = ctypes.CDLL(APPLICATION_SERVICES)
core_graphics.CGEventCreateMouseEvent.restype = ctypes.c_void_p
core_graphics.CGEventCreateMouseEvent.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    CGPoint,
    ctypes.c_uint32,
]
core_graphics.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
core_graphics.CFRelease.argtypes = [ctypes.c_void_p]
try:
    core_graphics.CGEventSetIntegerValueField.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int64,
    ]
except AttributeError:
    pass


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return result.stdout.strip()


def osascript(script: str, args: list[str] | None = None) -> str:
    cmd = ["osascript", "-e", script]
    if args:
        cmd.extend(args)
    return run(cmd)


def mouse_event(event_type: int, x: float, y: float, click_state: int = 1) -> None:
    event = core_graphics.CGEventCreateMouseEvent(
        None,
        event_type,
        CGPoint(x, y),
        0,
    )
    try:
        core_graphics.CGEventSetIntegerValueField(event, 1, click_state)
    except AttributeError:
        pass
    core_graphics.CGEventPost(0, event)
    core_graphics.CFRelease(event)


def click(x: float, y: float, count: int = 1) -> None:
    for current in range(1, count + 1):
        mouse_event(5, x, y, current)
        mouse_event(1, x, y, current)
        mouse_event(2, x, y, current)
        time.sleep(0.08)


def activate_windows_app(window_title: str | None) -> None:
    if window_title:
        script = '''
on run argv
    set targetTitle to item 1 of argv
    tell application "Windows App" to activate
    tell application "System Events"
        tell process "Windows App"
            set frontmost to true
            repeat with w in windows
                try
                    if (name of w) contains targetTitle then
                        perform action "AXRaise" of w
                        exit repeat
                    end if
                end try
            end repeat
        end tell
    end tell
end run
'''
        osascript(script, [window_title])
    else:
        script = '''
tell application "Windows App" to activate
tell application "System Events"
    tell process "Windows App"
        set frontmost to true
    end tell
end tell
'''
        osascript(script)


def list_windows() -> str:
    script = r'''
tell application "System Events"
    tell process "Windows App"
        set output to {}
        repeat with w in windows
            try
                copy (name of w) to end of output
            end try
        end repeat
        return output as text
    end tell
end tell
'''
    return osascript(script)


def capture(output: Path, rect: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["screencapture", "-x"]
    if rect:
        cmd.extend(["-R", rect])
    cmd.append(str(output))
    subprocess.run(cmd, check=True)


def crop(source: Path, output: Path, width: int, height: int, offset_y: int, offset_x: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "sips",
        "-c",
        str(height),
        str(width),
        "--cropOffset",
        str(offset_y),
        str(offset_x),
        str(source),
        "--out",
        str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def normalize_paddle_page(page: dict) -> list[dict]:
    data = page.get("res", page)
    texts = data.get("rec_texts", [])
    scores = data.get("rec_scores", [])
    boxes = data.get("rec_boxes", [])
    polys = data.get("rec_polys") or data.get("dt_polys") or []

    lines = []
    for index, text in enumerate(texts):
        lines.append(
            {
                "text": text,
                "score": scores[index] if index < len(scores) else None,
                "bbox": boxes[index] if index < len(boxes) else None,
                "quad": polys[index] if index < len(polys) else None,
            }
        )
    return lines


def render_ocr_output(lines: list[dict], output_format: str = "json") -> str:
    if output_format == "text":
        return "\n".join(line["text"] for line in lines)
    if output_format == "json":
        return json.dumps(lines, ensure_ascii=False, indent=2)
    raise ValueError(f"Unsupported OCR output format: {output_format}")


def normalize_aistudio_ocr_result(payload: dict) -> list[dict]:
    result = payload.get("result", payload)
    lines = []
    for page in result.get("ocrResults", []):
        pruned = page.get("prunedResult") or {}
        texts = pruned.get("rec_texts", [])
        scores = pruned.get("rec_scores", [])
        boxes = pruned.get("rec_boxes", [])
        for index, text in enumerate(texts):
            if not text:
                continue
            if index >= len(boxes):
                continue
            left, top, right, bottom = [int(value) for value in boxes[index]]
            lines.append(
                {
                    "text": text,
                    "score": scores[index] if index < len(scores) else None,
                    "bbox": [left, top, right, bottom],
                    "quad": [[left, top], [right, top], [right, bottom], [left, bottom]],
                }
            )
    return lines


def resolve_aistudio_ocr_config(token: str | None = None, api_url: str | None = None) -> tuple[str, str]:
    api_url = api_url or os.environ.get("AISTUDIO_OCR_API_URL")
    token = token or os.environ.get("AISTUDIO_OCR_TOKEN")
    if not api_url:
        raise RuntimeError("缺少 AI Studio OCR API URL，请设置 AISTUDIO_OCR_API_URL。")
    if not token:
        raise RuntimeError("缺少 AI Studio OCR token，请设置 AISTUDIO_OCR_TOKEN。")
    return api_url, token


def infer_file_type(image: Path) -> int:
    return 0 if image.suffix.lower() == ".pdf" else 1


def load_paddle_ocr():
    try:
        from paddleocr import PaddleOCR
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PaddleOCR 未安装。请先用 Python 3.13 虚拟环境安装 paddleocr 和 paddlepaddle。"
        ) from exc
    return PaddleOCR


def ocr(
    image: Path,
    lang: str = "ch",
    output_format: str = "json",
    *,
    token: str | None = None,
    api_url: str | None = None,
    session=None,
) -> str:
    del lang  # AI Studio OCR 当前走服务端默认语言能力
    api_url, token = resolve_aistudio_ocr_config(token=token, api_url=api_url)
    session = session or requests.Session()
    payload = {
        "file": base64.b64encode(image.read_bytes()).decode("ascii"),
        "fileType": infer_file_type(image),
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useTextlineOrientation": False,
    }
    response = session.post(
        api_url,
        json=payload,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    response.raise_for_status()
    lines = normalize_aistudio_ocr_result(response.json())
    return render_ocr_output(lines, output_format=output_format)


def send_key(keycode: int) -> None:
    osascript(
        f'''
tell application "System Events"
    key code {keycode}
end tell
'''
    )


def send_text(text: str) -> None:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    osascript(
        f'''
tell application "System Events"
    keystroke "{escaped}"
end tell
'''
    )


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local macOS GUI toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-windows", help="List Windows App window titles")

    activate = sub.add_parser("activate", help="Activate Windows App")
    activate.add_argument("--title", help="Window title substring to raise")

    shot = sub.add_parser("capture", help="Capture screen or region")
    shot.add_argument("output", type=Path)
    shot.add_argument("--rect", help='Rect like "0,30,2243,1266"')

    crop_cmd = sub.add_parser("crop", help="Crop an existing image with sips")
    crop_cmd.add_argument("source", type=Path)
    crop_cmd.add_argument("output", type=Path)
    crop_cmd.add_argument("--width", type=int, required=True)
    crop_cmd.add_argument("--height", type=int, required=True)
    crop_cmd.add_argument("--offset-y", type=int, required=True)
    crop_cmd.add_argument("--offset-x", type=int, required=True)

    ocr_cmd = sub.add_parser("ocr", help="Run PaddleOCR")
    ocr_cmd.add_argument("image", type=Path)
    ocr_cmd.add_argument("--lang", default="ch")
    ocr_cmd.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="json 会输出文本+坐标，text 仅输出纯文本",
    )

    click_cmd = sub.add_parser("click", help="Click at absolute screen coordinates")
    click_cmd.add_argument("x", type=float)
    click_cmd.add_argument("y", type=float)
    click_cmd.add_argument("--count", type=int, default=1)

    key_cmd = sub.add_parser("key", help="Send a macOS key code")
    key_cmd.add_argument("keycode", type=int)

    text_cmd = sub.add_parser("text", help="Type literal text")
    text_cmd.add_argument("value")

    doctor = sub.add_parser("doctor", help="Check local dependencies")
    doctor.add_argument("--json", action="store_true")

    return parser


def doctor(as_json: bool) -> int:
    venv_python = Path(__file__).with_name(".venv").joinpath("bin/python")
    checks = {
        "osascript": shutil_which("osascript"),
        "screencapture": shutil_which("screencapture"),
        "sips": shutil_which("sips"),
        "python3": shutil_which("python3"),
        "venv_python": str(venv_python) if venv_python.exists() else None,
        "aistudio_ocr_api_url_configured": bool(os.environ.get("AISTUDIO_OCR_API_URL")),
        "aistudio_ocr_token_configured": bool(os.environ.get("AISTUDIO_OCR_TOKEN")),
        "aistudio_ocr_configured": bool(os.environ.get("AISTUDIO_OCR_TOKEN") and os.environ.get("AISTUDIO_OCR_API_URL")),
    }
    checks["xcode_license_ready"] = xcode_license_ready()
    checks["paddle_ready"] = paddle_ready()

    if as_json:
        import json

        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 0

    for key, value in checks.items():
        print(f"{key}: {value}")
    return 0


def shutil_which(name: str) -> str | None:
    return subprocess.run(
        ["which", name],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip() or None


def xcode_license_ready() -> bool:
    result = subprocess.run(
        ["xcodebuild", "-license", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def paddle_ready() -> bool:
    try:
        with (
            warnings.catch_warnings(),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            warnings.simplefilter("ignore")
            load_paddle_ocr()
        return True
    except Exception:
        return False


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-windows":
        print(list_windows())
        return 0
    if args.command == "activate":
        activate_windows_app(args.title)
        return 0
    if args.command == "capture":
        capture(args.output, args.rect)
        print(args.output)
        return 0
    if args.command == "crop":
        crop(args.source, args.output, args.width, args.height, args.offset_y, args.offset_x)
        print(args.output)
        return 0
    if args.command == "ocr":
        print(ocr(args.image, args.lang, args.format))
        return 0
    if args.command == "click":
        click(args.x, args.y, args.count)
        return 0
    if args.command == "key":
        send_key(args.keycode)
        return 0
    if args.command == "text":
        send_text(args.value)
        return 0
    if args.command == "doctor":
        return doctor(args.json)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
