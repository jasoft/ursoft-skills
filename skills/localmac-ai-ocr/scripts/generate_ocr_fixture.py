#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"
IMAGE_PATH = FIXTURE_DIR / "ocr_fixture.png"
SPEC_PATH = FIXTURE_DIR / "ocr_fixture_spec.json"

WIDTH = 1600
HEIGHT = 900
BG = "#f4f6fb"


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise RuntimeError("找不到可用中文字体")


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, x: int, y: int, size: int, color: str) -> None:
    if kind == "circle":
        draw.ellipse((x, y, x + size, y + size), fill=color)
    elif kind == "square":
        draw.rounded_rectangle((x, y, x + size, y + size), radius=10, fill=color)
    elif kind == "triangle":
        draw.polygon(
            [(x + size // 2, y), (x + size, y + size), (x, y + size)],
            fill=color,
        )
    elif kind == "diamond":
        draw.polygon(
            [(x + size // 2, y), (x + size, y + size // 2), (x + size // 2, y + size), (x, y + size // 2)],
            fill=color,
        )
    else:
        raise ValueError(f"unknown icon kind: {kind}")


def draw_text(draw: ImageDraw.ImageDraw, entries: list[dict], text: str, xy: tuple[int, int], text_font, fill: str = "#101828", tag: str | None = None) -> None:
    draw.text(xy, text, font=text_font, fill=fill)
    left, top, right, bottom = draw.textbbox(xy, text, font=text_font)
    entries.append(
        {
            "text": text,
            "bbox": [left, top, right, bottom],
            "center": [(left + right) // 2, (top + bottom) // 2],
            "tag": tag or text,
        }
    )


def make_fixture() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    title_font = font(40)
    label_font = font(24)
    body_font = font(32)
    small_font = font(22)

    entries: list[dict] = []

    draw.rounded_rectangle((40, 28, WIDTH - 40, 110), radius=24, fill="#ffffff")
    draw.rounded_rectangle((1250, 42, 1510, 94), radius=18, fill="#e8eefc")
    draw_text(draw, entries, "本地 OCR 控制台", (82, 46), title_font, fill="#0f172a", tag="title")
    draw_text(draw, entries, "查找(F12)", (1276, 55), label_font, fill="#1d4ed8", tag="action-find")
    draw_text(draw, entries, "自动点击", (1400, 55), label_font, fill="#1d4ed8", tag="action-click")

    panels = [
        ("circle", "#16a34a", "关注", "00700 腾讯控股", "522.000"),
        ("triangle", "#f97316", "观察", "09992 泡泡玛特", "208.400"),
        ("square", "#2563eb", "自选", "01810 小米集团-W", "34.100"),
        ("diamond", "#db2777", "提醒", "00388 港交所", "372.800"),
    ]
    start_x = 60
    card_y = 150
    card_w = 360
    card_h = 150
    gap = 20
    for index, (icon_kind, color, label, name, price) in enumerate(panels):
        x = start_x + index * (card_w + gap)
        draw.rounded_rectangle((x, card_y, x + card_w, card_y + card_h), radius=24, fill="#ffffff")
        draw_icon(draw, icon_kind, x + 24, card_y + 28, 36, color)
        draw_text(draw, entries, label, (x + 78, card_y + 26), label_font, fill="#475467", tag=f"panel-label-{index}")
        draw_text(draw, entries, name, (x + 24, card_y + 74), body_font, fill="#0f172a", tag=name)
        draw_text(draw, entries, price, (x + 24, card_y + 112), label_font, fill="#16a34a", tag=price)

    draw.rounded_rectangle((40, 340, 1110, 840), radius=24, fill="#ffffff")
    draw.rounded_rectangle((1140, 340, 1560, 840), radius=24, fill="#ffffff")
    draw_text(draw, entries, "自选列表", (74, 372), body_font, fill="#0f172a", tag="watchlist")
    draw_text(draw, entries, "指令面板", (1174, 372), body_font, fill="#0f172a", tag="command-panel")

    headers = ["代码", "名称", "最新", "状态"]
    header_x = [88, 232, 770, 970]
    for text, x in zip(headers, header_x, strict=True):
        draw_text(draw, entries, text, (x, 428), label_font, fill="#667085", tag=f"header-{text}")

    rows = [
        ("00700", "腾讯控股", "522.000", "买入", "circle", "#16a34a"),
        ("09992", "泡泡玛特", "208.400", "观察", "triangle", "#f97316"),
        ("01810", "小米集团-W", "34.100", "自选", "square", "#2563eb"),
    ]
    row_y = 480
    row_gap = 96
    for index, (code, name, price, state, icon_kind, color) in enumerate(rows):
        top = row_y + index * row_gap
        draw.rounded_rectangle((64, top - 16, 1088, top + 56), radius=18, fill="#f8fafc")
        draw_icon(draw, icon_kind, 88, top - 2, 28, color)
        draw_text(draw, entries, code, (136, top - 6), body_font, fill="#0f172a", tag=code)
        draw_text(draw, entries, name, (232, top - 6), body_font, fill="#0f172a", tag=name)
        draw_text(draw, entries, price, (770, top - 6), body_font, fill="#0f172a", tag=price)
        draw_text(draw, entries, state, (970, top - 6), body_font, fill="#475467", tag=state)

    commands = [
        "搜索腾讯控股",
        "定位 00700",
        "点击价格框",
        "导出标注图",
    ]
    for idx, command in enumerate(commands):
        y = 446 + idx * 82
        draw.rounded_rectangle((1174, y, 1528, y + 56), radius=16, fill="#eef2ff")
        draw_text(draw, entries, command, (1198, y + 10), small_font, fill="#3730a3", tag=command)

    image.save(IMAGE_PATH)
    SPEC_PATH.write_text(
        json.dumps(
            {
                "image": "fixtures/ocr_fixture.png",
                "size": [WIDTH, HEIGHT],
                "entries": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    make_fixture()
