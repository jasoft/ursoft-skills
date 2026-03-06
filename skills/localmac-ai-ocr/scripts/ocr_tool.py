#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import io
import json
import os
import re
import time
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
warnings.filterwarnings(
    "ignore",
    message=r"urllib3 .* doesn't match a supported version!",
)
import requests

import gui_toolkit
from generate_ocr_fixture import IMAGE_PATH, SPEC_PATH, make_fixture

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


Item = dict
DEFAULT_LOCK_PATH = Path("/tmp/localmac-ocr.lock")
DEFAULT_LOCK_TIMEOUT = 600.0
LOCKED_COMMANDS = {"ocr", "find", "annotate", "crop-matches", "click-text", "rows", "benchmark"}
BACKEND_CHOICES = ["auto", "aistudio-ocr", "paddle"]


@contextlib.contextmanager
def muted_backend():
    with (
        warnings.catch_warnings(),
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        warnings.simplefilter("ignore")
        yield


@lru_cache(maxsize=4)
def get_engine(lang: str):
    with muted_backend():
        PaddleOCR = gui_toolkit.load_paddle_ocr()
        return PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=lang,
        )


def ocr_image(image_path: Path, lang: str = "ch", min_score: float = 0.0, sort: str = "reading") -> list[Item]:
    return run_ocr_backend(
        image_path,
        backend="paddle",
        lang=lang,
        min_score=min_score,
        sort=sort,
    )


def run_ocr_backend(
    image_path: Path,
    backend: str = "auto",
    lang: str = "ch",
    min_score: float = 0.0,
    sort: str = "reading",
    aistudio_api_url: str | None = None,
    aistudio_token: str | None = None,
) -> list[Item]:
    image_path = Path(image_path)
    backend = resolve_backend_choice(backend)
    if backend == "aistudio-ocr":
        items = aistudio_ocr(
            image_path,
            api_url=aistudio_api_url,
            token=aistudio_token,
        )
    elif backend == "paddle":
        with muted_backend():
            result = get_engine(lang).predict(str(image_path))

        items: list[Item] = []
        for page in result:
            page_json = page.json if hasattr(page, "json") else page
            items.extend(gui_toolkit.normalize_paddle_page(page_json))
    else:
        raise ValueError(f"Unsupported OCR backend: {backend}")

    items = [item for item in items if (item.get("score") or 1.0) >= min_score and item.get("text")]
    return sort_items(items, mode=sort)


def normalize_aistudio_ocr_response(payload: dict) -> list[Item]:
    result = payload.get("result", payload)
    items: list[Item] = []
    for page in result.get("ocrResults", []):
        pruned = page.get("prunedResult") or {}
        texts = pruned.get("rec_texts", [])
        scores = pruned.get("rec_scores", [])
        boxes = pruned.get("rec_boxes", [])
        for index, text in enumerate(texts):
            if not text:
                continue
            bbox = boxes[index] if index < len(boxes) else None
            if not bbox:
                continue
            left, top, right, bottom = [int(value) for value in bbox]
            items.append(
                {
                    "text": text,
                    "score": scores[index] if index < len(scores) else None,
                    "bbox": [left, top, right, bottom],
                    "quad": [[left, top], [right, top], [right, bottom], [left, bottom]],
                }
            )
    return items


def resolve_aistudio_ocr_config(
    api_url: str | None = None,
    token: str | None = None,
) -> tuple[str, str]:
    api_url = api_url or os.environ.get("AISTUDIO_OCR_API_URL")
    token = token or os.environ.get("AISTUDIO_OCR_TOKEN")
    if not api_url:
        raise RuntimeError("缺少 AI Studio OCR API URL，请设置 AISTUDIO_OCR_API_URL。")
    if not token:
        raise RuntimeError("缺少 AI Studio OCR token，请设置 AISTUDIO_OCR_TOKEN。")
    return api_url, token


def aistudio_ocr_configured() -> bool:
    return bool(os.environ.get("AISTUDIO_OCR_TOKEN") and os.environ.get("AISTUDIO_OCR_API_URL"))


def infer_aistudio_file_type(image_path: Path) -> int:
    return 0 if image_path.suffix.lower() == ".pdf" else 1


def aistudio_ocr(
    image_path: Path,
    api_url: str | None = None,
    token: str | None = None,
    session=None,
) -> list[Item]:
    api_url, token = resolve_aistudio_ocr_config(api_url, token)
    session = session or requests.Session()
    file_bytes = Path(image_path).read_bytes()
    payload = {
        "file": base64.b64encode(file_bytes).decode("ascii"),
        "fileType": infer_aistudio_file_type(Path(image_path)),
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
    payload = response.json()
    if payload.get("errorCode") not in (None, 0):
        raise RuntimeError(f"AI Studio OCR 调用失败: {payload}")
    return normalize_aistudio_ocr_response(payload)


def resolve_backend_choice(backend: str) -> str:
    if backend != "auto":
        return backend

    env_backend = os.environ.get("OCR_DEFAULT_BACKEND", "").strip()
    if env_backend in {"aistudio-ocr", "paddle"}:
        return env_backend

    if aistudio_ocr_configured():
        return "aistudio-ocr"
    return "paddle"


def command_needs_lock(command: str) -> bool:
    return command in LOCKED_COMMANDS


@contextlib.contextmanager
def acquire_ocr_lock(
    lock_path: Path,
    timeout_seconds: float = DEFAULT_LOCK_TIMEOUT,
    poll_interval: float = 0.2,
):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + max(0.0, timeout_seconds)

    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({"pid": os.getpid(), "time": int(time.time())}, ensure_ascii=False))
            handle.flush()
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                raise TimeoutError(f"OCR 正在被其他进程占用，等待 {timeout_seconds:.1f}s 仍未拿到锁：{lock_path}")
            time.sleep(poll_interval)

    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            handle.seek(0)
            handle.truncate()
            handle.flush()
        with contextlib.suppress(OSError):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def maybe_run_with_ocr_lock(args, work: Callable[[], int]) -> int:
    if getattr(args, "no_lock", False) or not command_needs_lock(args.command):
        return work()

    lock_path = Path(getattr(args, "lock_path", DEFAULT_LOCK_PATH))
    timeout_seconds = float(getattr(args, "lock_timeout", DEFAULT_LOCK_TIMEOUT))
    with acquire_ocr_lock(lock_path, timeout_seconds=timeout_seconds):
        return work()


def benchmark_backends(
    image_path: Path,
    backends: list[str],
    repeat: int = 2,
    runner: Callable[..., list[Item]] = run_ocr_backend,
    **kwargs,
) -> list[dict]:
    report: list[dict] = []
    for backend in backends:
        durations: list[float] = []
        item_count = 0
        for _ in range(repeat):
            started = time.perf_counter()
            items = runner(image_path, backend=backend, **kwargs)
            ended = time.perf_counter()
            durations.append(ended - started)
            item_count = len(items)
        report.append(
            {
                "backend": backend,
                "repeat": repeat,
                "item_count": item_count,
                "avg_seconds": round(sum(durations) / len(durations), 4),
                "min_seconds": round(min(durations), 4),
                "max_seconds": round(max(durations), 4),
            }
        )
    return report


def sort_items(items: list[Item], mode: str = "reading") -> list[Item]:
    if mode == "score":
        return sorted(items, key=lambda item: item.get("score") or 0.0, reverse=True)
    if mode == "area":
        return sorted(items, key=lambda item: bbox_area(item["bbox"]), reverse=True)
    return sorted(items, key=lambda item: (item["bbox"][1], item["bbox"][0]))


def bbox_area(bbox: list[int]) -> int:
    return max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])


def transform_items(items: list[Item], image_size: tuple[int, int], relative: bool = False, include_center: bool = False) -> list[Item]:
    width, height = image_size
    transformed: list[Item] = []
    for item in items:
        row = dict(item)
        left, top, right, bottom = row["bbox"]
        if include_center:
            row["center"] = [(left + right) // 2, (top + bottom) // 2]
        if relative:
            row["bbox_relative"] = [
                round(left / width, 4),
                round(top / height, 4),
                round(right / width, 4),
                round(bottom / height, 4),
            ]
        transformed.append(row)
    return transformed


def group_rows(items: list[Item], row_tolerance: float = 0.55) -> list[Item]:
    if not items:
        return []

    reading = sort_items(items, mode="reading")
    rows: list[list[Item]] = []
    for item in reading:
        placed = False
        item_mid = (item["bbox"][1] + item["bbox"][3]) / 2
        item_height = max(1, item["bbox"][3] - item["bbox"][1])
        for row in rows:
            row_top = min(entry["bbox"][1] for entry in row)
            row_bottom = max(entry["bbox"][3] for entry in row)
            row_mid = (row_top + row_bottom) / 2
            row_height = max(1, row_bottom - row_top)
            if abs(item_mid - row_mid) <= max(item_height, row_height) * row_tolerance:
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])

    grouped: list[Item] = []
    for row in rows:
        ordered = sorted(row, key=lambda entry: entry["bbox"][0])
        left = min(entry["bbox"][0] for entry in ordered)
        top = min(entry["bbox"][1] for entry in ordered)
        right = max(entry["bbox"][2] for entry in ordered)
        bottom = max(entry["bbox"][3] for entry in ordered)
        grouped.append(
            {
                "text": " ".join(entry["text"] for entry in ordered),
                "score": round(sum(entry.get("score") or 0.0 for entry in ordered) / len(ordered), 6),
                "bbox": [left, top, right, bottom],
                "quad": [[left, top], [right, top], [right, bottom], [left, bottom]],
                "items": ordered,
            }
        )
    return sort_items(grouped, mode="reading")


def find_matches(items: list[Item], query: str, mode: str = "contains", ignore_case: bool = True, first: bool = False) -> list[Item]:
    flags = re.IGNORECASE if ignore_case else 0
    found: list[Item] = []

    for item in items:
        text = item["text"]
        if mode == "exact":
            match = text.casefold() == query.casefold() if ignore_case else text == query
        elif mode == "regex":
            match = re.search(query, text, flags=flags) is not None
        else:
            match = query.casefold() in text.casefold() if ignore_case else query in text
        if match:
            found.append(item)
            if first:
                break
    return found


def select_match_index(matches: list[Item], index: int | None) -> list[Item]:
    if index is None:
        return matches
    if index < 1:
        raise SystemExit("--index 必须从 1 开始")
    if index > len(matches):
        raise SystemExit(f"--index={index} 超出命中范围，当前只有 {len(matches)} 个结果")
    return [matches[index - 1]]


def crop_matches(image_path: Path, matches: list[Item], output_dir: Path, padding: int = 10) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image = Image.open(image_path)
    outputs: list[Path] = []
    for index, match in enumerate(matches, start=1):
        left, top, right, bottom = match["bbox"]
        crop = image.crop(
            (
                max(0, left - padding),
                max(0, top - padding),
                min(image.width, right + padding),
                min(image.height, bottom + padding),
            )
        )
        filename = f"{index:02d}_{sanitize_filename(match['text'])}.png"
        target = output_dir / filename
        crop.save(target)
        outputs.append(target)
    return outputs


def annotation_lines(
    item: Item,
    *,
    include_text: bool = True,
    include_center: bool = True,
    include_score: bool = True,
) -> list[str]:
    left, top, right, bottom = item["bbox"]
    parts: list[str] = []
    if include_text:
        text = str(item.get("text") or "").strip()
        if text:
            parts.append(text if len(text) <= 36 else f"{text[:33]}...")
    if include_center:
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        parts.append(f"center=({center_x},{center_y})")
    if include_score:
        score = item.get("score")
        if score is not None:
            parts.append(f"score={float(score):.3f}")
    return parts


def annotate_image(
    image_path: Path,
    output_path: Path,
    items: list[Item],
    color: str = "#e11d48",
    *,
    include_text: bool = True,
    include_center: bool = True,
    include_score: bool = True,
) -> Path:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    label_font = load_font(20)
    for item in items:
        left, top, right, bottom = item["bbox"]
        draw.rounded_rectangle((left, top, right, bottom), outline=color, width=3, radius=6)
        lines = annotation_lines(
            item,
            include_text=include_text,
            include_center=include_center,
            include_score=include_score,
        )
        if not lines:
            continue
        label = "\n".join(lines)
        label_bbox = draw.multiline_textbbox((left, top), label, font=label_font, spacing=4)
        label_height = label_bbox[3] - label_bbox[1]
        label_width = label_bbox[2] - label_bbox[0]
        label_top = max(0, top - label_height - 10)
        label_bg = (left, label_top, left + label_width + 16, label_top + label_height + 8)
        draw.rounded_rectangle(label_bg, radius=8, fill=color)
        draw.multiline_text((label_bg[0] + 8, label_bg[1] + 4), label, font=label_font, fill="#ffffff", spacing=4)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def click_match(
    match: Item,
    image_size_value: tuple[int, int],
    clicker: Callable[..., None] = gui_toolkit.click,
    count: int = 1,
    screen_rect: str | None = None,
) -> tuple[int, int]:
    left, top, right, bottom = match["bbox"]
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    screen_x, screen_y = gui_toolkit.image_point_to_screen_point(
        center_x,
        center_y,
        image_size_value,
        screen_rect=screen_rect,
    )
    clicker(screen_x, screen_y, count=count)
    return round(screen_x), round(screen_y)


def render_items(items: list[Item], output_format: str = "json") -> str:
    if output_format == "json":
        return json.dumps(items, ensure_ascii=False, indent=2)
    if output_format == "text":
        return "\n".join(item["text"] for item in items)
    if output_format == "tsv":
        rows = ["text\tscore\tbbox"]
        for item in items:
            rows.append(f"{item['text']}\t{item.get('score', '')}\t{item['bbox']}")
        return "\n".join(rows)
    raise ValueError(f"Unsupported output format: {output_format}")


def sanitize_filename(text: str) -> str:
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text).strip("_")
    return value or "match"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def image_size(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as image:
        return image.width, image.height


def doctor() -> dict:
    return {
        "python": os.environ.get("PYTHONEXECUTABLE") or os.sys.executable,
        "paddle_ready": gui_toolkit.paddle_ready(),
        "aistudio_configured": aistudio_ocr_configured(),
        "aistudio_api_url_configured": bool(os.environ.get("AISTUDIO_OCR_API_URL")),
        "aistudio_token_configured": bool(os.environ.get("AISTUDIO_OCR_TOKEN")),
        "preferred_backend": resolve_backend_choice("auto"),
        "fixture_image": str(IMAGE_PATH),
        "fixture_spec": str(SPEC_PATH),
    }


def parse_items(image: Path, args) -> tuple[list[Item], tuple[int, int]]:
    items = run_ocr_backend(
        image,
        backend=args.backend,
        lang=args.lang,
        min_score=args.min_score,
        sort=args.sort,
        aistudio_api_url=getattr(args, "aistudio_api_url", None),
        aistudio_token=getattr(args, "aistudio_token", None),
    )
    if getattr(args, "rows", False):
        items = group_rows(items)
    size = image_size(image)
    items = transform_items(items, size, relative=args.relative, include_center=args.center)
    return items, size


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PaddleOCR full toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    fixture = sub.add_parser("fixture", help="生成测试截图和基准坐标")
    fixture.add_argument("--print-paths", action="store_true")

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("image", type=Path)
    shared.add_argument("--lang", default="ch")
    shared.add_argument("--min-score", type=float, default=0.0)
    shared.add_argument("--sort", choices=["reading", "score", "area"], default="reading")
    shared.add_argument("--relative", action="store_true")
    shared.add_argument("--center", action="store_true")
    shared.add_argument("--rows", action="store_true")
    shared.add_argument("--backend", choices=BACKEND_CHOICES, default="auto")
    shared.add_argument("--aistudio-api-url")
    shared.add_argument("--aistudio-token")
    shared.add_argument("--screen-rect", help='截图对应的屏幕区域，格式 "x,y,width,height"，单位为屏幕 point')
    shared.add_argument("--annotate-output", type=Path, help="把识别结果画框到图片文件，便于 agent 复核框、坐标和置信度")
    shared.add_argument("--annotate-color", default="#e11d48", help="标注图的框线与标签颜色，默认 #e11d48")
    shared.add_argument("--annotate-no-text", action="store_true", help="标注图标签里不显示识别文本")
    shared.add_argument("--annotate-no-center", action="store_true", help="标注图标签里不显示中心坐标")
    shared.add_argument("--annotate-no-score", action="store_true", help="标注图标签里不显示置信度")
    shared.add_argument("--lock-path", default=str(DEFAULT_LOCK_PATH))
    shared.add_argument("--lock-timeout", type=float, default=DEFAULT_LOCK_TIMEOUT)
    shared.add_argument("--no-lock", action="store_true")

    ocr_cmd = sub.add_parser("ocr", help="执行 OCR", parents=[shared])
    ocr_cmd.add_argument("--format", choices=["json", "text", "tsv"], default="json")

    find_cmd = sub.add_parser("find", help="按文本查找框", parents=[shared])
    find_cmd.add_argument("--query", required=True)
    find_cmd.add_argument("--mode", choices=["exact", "contains", "regex"], default="contains")
    find_cmd.add_argument("--first", action="store_true")
    find_cmd.add_argument("--index", type=int, help="只返回第几个命中项，按阅读顺序从 1 开始")
    find_cmd.add_argument("--format", choices=["json", "text", "tsv"], default="json")

    annotate_cmd = sub.add_parser("annotate", help="输出带框标注图", parents=[shared])
    annotate_cmd.add_argument("output", type=Path)
    annotate_cmd.add_argument("--query")
    annotate_cmd.add_argument("--mode", choices=["exact", "contains", "regex"], default="contains")

    crop_cmd = sub.add_parser("crop-matches", help="导出命中文本裁图", parents=[shared])
    crop_cmd.add_argument("output_dir", type=Path)
    crop_cmd.add_argument("--query", required=True)
    crop_cmd.add_argument("--mode", choices=["exact", "contains", "regex"], default="contains")

    click_cmd = sub.add_parser("click-text", help="按识别框中心点击", parents=[shared])
    click_cmd.add_argument("--query", required=True)
    click_cmd.add_argument("--mode", choices=["exact", "contains", "regex"], default="contains")
    click_cmd.add_argument("--count", type=int, default=1)
    click_cmd.add_argument("--first", action="store_true", help="存在多个命中时仍点击第一个，否则直接报错")
    click_cmd.add_argument("--index", type=int, help="点击第几个命中项，按阅读顺序从 1 开始")

    rows_cmd = sub.add_parser("rows", help="按行分组输出", parents=[shared])
    rows_cmd.add_argument("--format", choices=["json", "text", "tsv"], default="json")

    bench = sub.add_parser("benchmark", help="对比不同 OCR 后端耗时")
    bench.add_argument("image", type=Path)
    bench.add_argument("--lang", default="ch")
    bench.add_argument("--repeat", type=int, default=2)
    bench.add_argument("--backend", choices=BACKEND_CHOICES, action="append", dest="backends")
    bench.add_argument("--aistudio-api-url")
    bench.add_argument("--aistudio-token")
    bench.add_argument("--min-score", type=float, default=0.0)
    bench.add_argument("--sort", choices=["reading", "score", "area"], default="reading")
    bench.add_argument("--lock-path", default=str(DEFAULT_LOCK_PATH))
    bench.add_argument("--lock-timeout", type=float, default=DEFAULT_LOCK_TIMEOUT)
    bench.add_argument("--no-lock", action="store_true")

    sub.add_parser("doctor", help="检查 Paddle 和 fixture 状态")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    def run_command() -> int:
        if args.command == "fixture":
            make_fixture()
            if args.print_paths:
                print(json.dumps({"image": str(IMAGE_PATH), "spec": str(SPEC_PATH)}, ensure_ascii=False, indent=2))
            return 0

        if args.command == "doctor":
            print(json.dumps(doctor(), ensure_ascii=False, indent=2))
            return 0

        if args.command == "benchmark":
            backends = args.backends or ["auto"]
            report = benchmark_backends(
                args.image,
                backends=backends,
                repeat=args.repeat,
                lang=args.lang,
                min_score=args.min_score,
                sort=args.sort,
                aistudio_api_url=args.aistudio_api_url,
                aistudio_token=args.aistudio_token,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        if args.command == "rows":
            raw_items = run_ocr_backend(
                args.image,
                backend=args.backend,
                lang=args.lang,
                min_score=args.min_score,
                sort=args.sort,
                aistudio_api_url=args.aistudio_api_url,
                aistudio_token=args.aistudio_token,
            )
            rows = transform_items(group_rows(raw_items), image_size(args.image), relative=args.relative, include_center=args.center)
            print(render_items(rows, args.format))
            return 0

        items, size = parse_items(args.image, args)

        if getattr(args, "annotate_output", None):
            annotate_image(
                args.image,
                args.annotate_output,
                items,
                color=args.annotate_color,
                include_text=not args.annotate_no_text,
                include_center=not args.annotate_no_center,
                include_score=not args.annotate_no_score,
            )

        if args.command == "ocr":
            print(render_items(items, args.format))
            return 0

        if args.command == "find":
            matches = find_matches(items, args.query, mode=args.mode, first=args.first)
            matches = select_match_index(matches, args.index)
            print(render_items(matches, args.format))
            return 0

        if args.command == "annotate":
            matches = items if not args.query else find_matches(items, args.query, mode=args.mode)
            annotate_image(
                args.image,
                args.output,
                matches,
                color=args.annotate_color,
                include_text=not args.annotate_no_text,
                include_center=not args.annotate_no_center,
                include_score=not args.annotate_no_score,
            )
            print(args.output)
            return 0

        if args.command == "crop-matches":
            matches = find_matches(items, args.query, mode=args.mode)
            outputs = crop_matches(args.image, matches, args.output_dir)
            print(json.dumps([str(path) for path in outputs], ensure_ascii=False, indent=2))
            return 0

        if args.command == "click-text":
            matches = find_matches(items, args.query, mode=args.mode, first=args.first)
            if not matches:
                raise SystemExit("未找到目标文本")
            matches = select_match_index(matches, args.index)
            if len(matches) > 1 and not args.first:
                raise SystemExit(f"命中 {len(matches)} 处文本，请先缩小截图范围或显式传 --first")
            x, y = click_match(
                matches[0],
                size,
                count=args.count,
                screen_rect=args.screen_rect,
            )
            print(json.dumps({"text": matches[0]["text"], "center": [x, y]}, ensure_ascii=False, indent=2))
            return 0

        parser.print_help()
        return 1

    return maybe_run_with_ocr_lock(args, run_command)


if __name__ == "__main__":
    raise SystemExit(main())
