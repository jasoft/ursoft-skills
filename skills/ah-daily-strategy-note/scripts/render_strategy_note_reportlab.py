from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


RED = colors.HexColor("#c0392b")
GREEN = colors.HexColor("#27ae60")
BLUE = colors.HexColor("#2980b9")
NAVY = colors.HexColor("#2c3e50")
LIGHT_BG = colors.HexColor("#fafafa")
SOFT_BG = colors.HexColor("#f0f4f8")
BORDER = colors.HexColor("#e0e0e0")
TEXT = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#666666")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an A/H daily strategy note Markdown file to PDF with ReportLab."
    )
    parser.add_argument("--input-markdown", required=True, help="Source Markdown path.")
    parser.add_argument("--output-pdf", required=True, help="Output PDF path.")
    parser.add_argument(
        "--hot-stocks-json",
        help="Optional JSON file with hot stock items.",
    )
    return parser.parse_args()


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def find_one(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"missing {label}")
    return match.group(1).strip()


def section_between(text: str, start: str, end: str | None = None) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise ValueError(f"missing section: {start}")
    start_index += len(start)
    if end is None:
        return text[start_index:].strip()
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise ValueError(f"missing section end: {end}")
    return text[start_index:end_index].strip()


def parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_indexes(block: str) -> list[dict[str, str]]:
    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("| 指数") or line.startswith("| ---"):
            continue
        cells = parse_table_row(line)
        if len(cells) != 4:
            continue
        rows.append(
            {
                "name": cells[0],
                "level": cells[1],
                "change": cells[2],
                "view": cells[3],
            }
        )
    return rows


def parse_bullets(block: str) -> list[str]:
    return [line[2:].strip() for line in block.splitlines() if line.strip().startswith("- ")]


def parse_market_block(block: str, label: str) -> dict[str, object]:
    today = find_one(r"(?s)#### 今日走势\s+(.+?)\s+#### 杀跌方向", block, f"{label} 今日走势")
    selloff = parse_bullets(find_one(r"(?s)#### 杀跌方向\s+(.+?)\s+#### 相对抗跌", block, f"{label} 杀跌方向"))
    defensive = parse_bullets(find_one(r"(?s)#### 相对抗跌\s+(.+?)\s+\*\*", block, f"{label} 相对抗跌"))
    summary = find_one(rf"\*\*{label}一句话：(.+?)\*\*", block, f"{label} 一句话")
    return {
        "today": " ".join(today.split()),
        "selloff": selloff,
        "defensive": defensive,
        "summary": " ".join(summary.split()),
    }


def parse_news(block: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    impacts: list[str] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- 【"):
            if current:
                if len(impacts) != 2:
                    raise ValueError(f"incomplete news item: {current['title']}")
                current["explanation"] = impacts[0]
                current["impact"] = impacts[1]
                items.append(current)
            match = re.match(r"- 【(.+?)】(.+)", line)
            if not match:
                raise ValueError(f"invalid news line: {line}")
            current = {"tag": match.group(1).strip(), "title": match.group(2).strip()}
            impacts = []
            continue
        if line.startswith("→") or line.startswith("  →"):
            impacts.append(line.split("→", 1)[1].strip())
    if current:
        if len(impacts) != 2:
            raise ValueError(f"incomplete news item: {current['title']}")
        current["explanation"] = impacts[0]
        current["impact"] = impacts[1]
        items.append(current)

    category_map = ["宏观", "政策", "盘后变量"]
    for index, item in enumerate(items):
        item["category"] = category_map[index] if index < len(category_map) else "变量"
    return items


def parse_markdown(text: str) -> dict[str, object]:
    risk_mode = find_one(
        r"^\| DAILY STRATEGY NOTE \\\| A/H EQUITIES \| (.+?) \|$",
        text,
        "risk mode",
    )
    title = find_one(r"^#\s+(.+)$", text, "title")
    meta = find_one(r"^\*\*(.+?)\*\*$", text, "meta")
    sources = find_one(r"^数据来源：(.+)$", text, "sources")
    key_takeaway = find_one(r"^\| \*\*核心\*\* \| (.+) \|$", text, "key takeaway")
    index_block = section_between(text, "## 主要指数收盘概览", "## 双栏结构（核心分析区）")
    a_block = section_between(text, "### 左栏 | A股观察", "### 右栏 | 港股观察")
    h_block = section_between(text, "### 右栏 | 港股观察", "## 头条新闻与核心驱动")
    news_block = section_between(text, "## 头条新闻与核心驱动", "## 策略")
    strategy_block = section_between(text, "## 策略", "## 明日观察")
    watch_block = section_between(text, "## 明日观察", "## FOOTER")
    footer_block = section_between(text, "## FOOTER", None)

    strategy_nature = find_one(r"- 性质：(.+)", strategy_block, "strategy nature")
    strategy_action = find_one(r"- 应对：(.+)", strategy_block, "strategy action")
    data_note = find_one(r"数据口径说明：(.+)", footer_block, "data note")
    footer_sources = find_one(r"Sources：(.+)", footer_block, "footer sources")

    return {
        "risk_mode": risk_mode,
        "title": title,
        "meta": meta,
        "sources": [item.strip() for item in sources.split("/")],
        "key_takeaway": key_takeaway,
        "indexes": parse_indexes(index_block),
        "a_share": parse_market_block(a_block, "A股"),
        "h_share": parse_market_block(h_block, "港股"),
        "news": parse_news(news_block),
        "strategy": {"nature": strategy_nature, "action": strategy_action},
        "tomorrow_watch": parse_bullets(watch_block),
        "data_note": data_note,
        "footer_sources": footer_sources,
    }


def register_fonts() -> tuple[str, str, str]:
    font_specs = [
        ("STHeitiLight", "/System/Library/Fonts/STHeiti Light.ttc"),
        ("STHeitiMedium", "/System/Library/Fonts/STHeiti Medium.ttc"),
        ("Songti", "/System/Library/Fonts/Supplemental/Songti.ttc"),
    ]
    for name, path in font_specs:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, path))
    return "STHeitiLight", "STHeitiMedium", "Songti"


def build_styles() -> dict[str, ParagraphStyle]:
    sans, sans_bold, serif = register_fonts()
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=18,
            leading=22,
            textColor=RED,
            spaceAfter=3,
        ),
        "submeta": ParagraphStyle(
            "submeta",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.5,
            leading=12,
            textColor=MUTED,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#888888"),
            alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=11.5,
            leading=14,
            textColor=colors.white,
        ),
        "card_name": ParagraphStyle(
            "card_name",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.5,
            leading=11,
            textColor=colors.HexColor("#555555"),
        ),
        "card_value": ParagraphStyle(
            "card_value",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=13.5,
            leading=16,
            textColor=TEXT,
        ),
        "card_change": ParagraphStyle(
            "card_change",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=10,
            leading=12,
        ),
        "card_view": ParagraphStyle(
            "card_view",
            parent=base["Normal"],
            fontName=sans,
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
        ),
        "block_title": ParagraphStyle(
            "block_title",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=12,
            leading=14,
            textColor=TEXT,
        ),
        "sub_title": ParagraphStyle(
            "sub_title",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName=sans,
            fontSize=10,
            leading=15,
            textColor=TEXT,
        ),
        "body_small": ParagraphStyle(
            "body_small",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.2,
            leading=13,
            textColor=TEXT,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.5,
            leading=14,
            textColor=TEXT,
            leftIndent=10,
            firstLineIndent=-10,
            spaceAfter=2,
        ),
        "summary_box": ParagraphStyle(
            "summary_box",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.5,
            leading=16,
            textColor=TEXT,
        ),
        "summary_line": ParagraphStyle(
            "summary_line",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=9.5,
            leading=14,
            textColor=TEXT,
        ),
        "hot_label": ParagraphStyle(
            "hot_label",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "hot_name": ParagraphStyle(
            "hot_name",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=11,
            leading=13,
            textColor=TEXT,
        ),
        "hot_change": ParagraphStyle(
            "hot_change",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=11,
            leading=13,
            alignment=TA_RIGHT,
        ),
        "news_title": ParagraphStyle(
            "news_title",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=10,
            leading=14,
            textColor=TEXT,
        ),
        "news_body": ParagraphStyle(
            "news_body",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.2,
            leading=13,
            textColor=TEXT,
        ),
        "news_impact": ParagraphStyle(
            "news_impact",
            parent=base["Normal"],
            fontName=sans,
            fontSize=9.2,
            leading=13,
            textColor=MUTED,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName=sans,
            fontSize=7.6,
            leading=10,
            textColor=colors.HexColor("#999999"),
            alignment=TA_LEFT,
        ),
        "footer_center": ParagraphStyle(
            "footer_center",
            parent=base["Normal"],
            fontName=sans,
            fontSize=7.6,
            leading=10,
            textColor=colors.HexColor("#999999"),
            alignment=TA_LEFT,
        ),
        "label_small": ParagraphStyle(
            "label_small",
            parent=base["Normal"],
            fontName=sans_bold,
            fontSize=8.5,
            leading=10,
            textColor=NAVY,
        ),
        "serif_quote": ParagraphStyle(
            "serif_quote",
            parent=base["Normal"],
            fontName=serif,
            fontSize=10,
            leading=15,
            textColor=TEXT,
        ),
    }
    return styles


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def rich(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def section_title(text: str, styles: dict[str, ParagraphStyle], width: float) -> Table:
    table = Table([[Paragraph(escape(text), styles["section"])]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def summary_box(text: str, styles: dict[str, ParagraphStyle], width: float) -> Table:
    box = Table([[para(text, styles["summary_box"])]], colWidths=[width])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 4, BLUE),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return box


def tag_color(tag: str) -> colors.Color:
    return {
        "利好": GREEN,
        "利空": RED,
        "中性": BLUE,
        "盘后": NAVY,
        "正面": GREEN,
        "负面": RED,
    }.get(tag, BLUE)


def index_card(item: dict[str, str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    change_style = ParagraphStyle(
        f"change_{item['name']}",
        parent=styles["card_change"],
        textColor=GREEN if item["change"].startswith("-") else RED,
    )
    flows = [
        para(item["name"], styles["card_name"]),
        Spacer(1, 2),
        para(item["level"], styles["card_value"]),
        para(item["change"], change_style),
        Spacer(1, 4),
        para(item["view"], styles["card_view"]),
    ]
    card = Table([[flows]], colWidths=[width])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("ROUNDEDCORNERS", [5, 5, 5, 5]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return card


def market_column(title: str, flag: str, block: dict[str, object], styles: dict[str, ParagraphStyle], width: float) -> Table:
    flows = [
        rich(
            f"<font color='#1a1a1a'><b>{escape(title)}</b></font>"
            f"<font color='#7f8c8d'>  {escape(flag)}</font>",
            styles["block_title"],
        ),
        Spacer(1, 6),
        Paragraph(escape("今日走势"), styles["sub_title"]),
        summary_box(str(block["today"]), styles, width - 24),
        Spacer(1, 8),
        Paragraph(escape("杀跌方向"), styles["sub_title"]),
    ]
    for item in block["selloff"]:
        flows.append(rich(f"• {escape(str(item))}", styles["bullet"]))
    flows.extend([Spacer(1, 4), Paragraph(escape("相对抗跌"), styles["sub_title"])])
    for item in block["defensive"]:
        flows.append(rich(f"• {escape(str(item))}", styles["bullet"]))
    flows.extend([Spacer(1, 6), para(str(block["summary"]), styles["summary_line"])])

    column = Table([[flows]], colWidths=[width])
    column.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return column


def hot_stock_card(item: dict[str, str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    pill_color = tag_color(item.get("tag", "中性"))
    label = Table([[Paragraph(escape(item["market"]), styles["hot_label"])]], colWidths=[46])
    label.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pill_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    change_style = ParagraphStyle(
        f"hot_change_{item['name']}",
        parent=styles["hot_change"],
        textColor=tag_color(item.get("tag", "中性")),
    )
    content = [
        [
            label,
            para(item["name"], styles["hot_name"]),
            para(item["change"], change_style),
        ],
        [
            "",
            para(item["comment"], styles["body_small"]),
            "",
        ],
    ]
    card = Table(content, colWidths=[52, width - 124, 72])
    card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("SPAN", (1, 1), (2, 1)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return card


def news_item(item: dict[str, str], styles: dict[str, ParagraphStyle], width: float) -> Table:
    color = tag_color(item["tag"])
    tag = Table([[Paragraph(escape(item["tag"]), styles["hot_label"])]], colWidths=[40])
    tag.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    category = rich(
        f"<font color='#7f8c8d'>{escape(item['category'])}</font>",
        styles["label_small"],
    )
    title = para(item["title"], styles["news_title"])
    head = Table([[tag, category, title]], colWidths=[48, 56, width - 104])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    block = Table(
        [
            [head],
            [para(item["explanation"], styles["news_body"])],
            [rich(f"<font color='#666666'>影响：</font>{escape(item['impact'])}", styles["news_impact"])],
        ],
        colWidths=[width],
    )
    block.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return block


def build_story(note: dict[str, object], hot_stocks: list[dict[str, str]], styles: dict[str, ParagraphStyle], doc_width: float) -> list[object]:
    story: list[object] = []

    header_left = [
        para(note["title"], styles["title"]),
        para(note["meta"], styles["submeta"]),
    ]
    header_right = [
        para("数据来源：" + " / ".join(note["sources"]), styles["meta"]),
        para("风险状态：" + str(note["risk_mode"]), styles["meta"]),
    ]
    header = Table(
        [[header_left, header_right]],
        colWidths=[doc_width * 0.65, doc_width * 0.35],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEBELOW", (0, 0), (-1, -1), 2.5, RED),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([header, Spacer(1, 10)])

    story.extend([section_title("核心观点", styles, doc_width), Spacer(1, 6)])
    story.extend([summary_box(str(note["key_takeaway"]), styles, doc_width), Spacer(1, 12)])

    story.extend([section_title("主要指数收盘概览", styles, doc_width), Spacer(1, 8)])
    gap = 10
    card_width = (doc_width - gap * 2) / 3
    cards = [index_card(item, styles, card_width) for item in note["indexes"]]
    rows = [
        cards[:3],
        cards[3:] + [Spacer(1, 1)],
    ]
    index_grid = Table(rows, colWidths=[card_width, card_width, card_width], hAlign="LEFT")
    index_grid.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), gap),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([index_grid, Spacer(1, 8)])

    col_gap = 14
    col_width = (doc_width - col_gap) / 2
    market_grid = Table(
        [
            [
                market_column("A股观察", "MAINLAND", note["a_share"], styles, col_width),
                market_column("港股观察", "HONG KONG", note["h_share"], styles, col_width),
            ]
        ],
        colWidths=[col_width, col_width],
    )
    market_grid.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), col_gap),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(KeepTogether([market_grid]))
    story.append(PageBreak())

    story.extend([section_title("热门股走势与评论", styles, doc_width), Spacer(1, 8)])
    hot_width = (doc_width - 12) / 2
    hot_cards = [hot_stock_card(item, styles, hot_width) for item in hot_stocks]
    hot_rows = []
    for index in range(0, len(hot_cards), 2):
        row = hot_cards[index:index + 2]
        if len(row) == 1:
            row.append(Spacer(1, 1))
        hot_rows.append(row)
    hot_grid = Table(hot_rows, colWidths=[hot_width, hot_width])
    hot_grid.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([hot_grid, Spacer(1, 6)])

    story.extend([section_title("头条新闻与核心驱动", styles, doc_width), Spacer(1, 8)])
    for item in note["news"]:
        story.extend([news_item(item, styles, doc_width), Spacer(1, 6)])

    bottom_left = [
        rich("<b>策略</b>", styles["block_title"]),
        Spacer(1, 6),
        rich("<font color='#2c3e50'><b>性质</b></font>", styles["sub_title"]),
        para(note["strategy"]["nature"], styles["body"]),
        Spacer(1, 6),
        rich("<font color='#2c3e50'><b>应对</b></font>", styles["sub_title"]),
        para(note["strategy"]["action"], styles["body"]),
    ]
    bottom_right = [rich("<b>明日观察</b>", styles["block_title"]), Spacer(1, 6)]
    for item in note["tomorrow_watch"]:
        bottom_right.append(rich(f"• {escape(item)}", styles["bullet"]))

    bottom = Table(
        [[bottom_left, bottom_right]],
        colWidths=[col_width, col_width],
    )
    bottom.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), col_gap),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([Spacer(1, 2), HRFlowable(width="100%", color=BORDER, thickness=1), Spacer(1, 5), bottom, Spacer(1, 4)])

    story.extend(
        [
            HRFlowable(width="100%", color=BORDER, thickness=1),
            Spacer(1, 3),
            para("数据口径说明：" + str(note["data_note"]), styles["footer"]),
            Spacer(1, 2),
            para("Sources：" + str(note["footer_sources"]), styles["footer_center"]),
        ]
    )
    return story


def load_hot_stocks(path: str | None) -> list[dict[str, str]]:
    if not path:
        return []
    payload = json.loads(read_text(path))
    if not isinstance(payload, list):
        raise ValueError("hot stocks JSON must be a list")
    required = {"market", "name", "change", "comment", "tag"}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"hot stock item {index} is invalid")
    return payload


def render_pdf(input_markdown: str, output_pdf: str, hot_stocks_json: str | None) -> None:
    note = parse_markdown(read_text(input_markdown))
    hot_stocks = load_hot_stocks(hot_stocks_json)
    styles = build_styles()

    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=str(note["title"]),
        author="Codex",
    )
    story = build_story(note, hot_stocks, styles, doc.width)
    doc.build(story)


def main() -> int:
    args = parse_args()
    render_pdf(args.input_markdown, args.output_pdf, args.hot_stocks_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
