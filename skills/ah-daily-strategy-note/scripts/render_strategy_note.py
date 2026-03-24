from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EXPECTED_INDEX_ORDER = ["上证", "深证", "创业板", "恒生", "恒生科技"]
REQUIRED_NEWS_CATEGORIES = {"宏观", "政策", "盘后变量"}
VALID_NEWS_TAGS = {"利空", "利好", "中性", "盘后"}
REQUIRED_TOP_LEVEL_KEYS = {
    "date",
    "coverage",
    "risk_mode",
    "sources",
    "key_takeaway",
    "indexes",
    "a_share",
    "h_share",
    "news",
    "strategy",
    "tomorrow_watch",
    "data_note",
}


def _require_keys(payload: dict, keys: set[str], context: str) -> None:
    missing = sorted(key for key in keys if key not in payload)
    if missing:
        raise ValueError(f"{context} missing required keys: {', '.join(missing)}")


def _require_non_empty_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value.strip()


def _validate_market_block(name: str, block: object) -> None:
    if not isinstance(block, dict):
        raise ValueError(f"{name} must be an object")

    _require_keys(block, {"today", "selloff", "defensive", "summary"}, name)
    _require_non_empty_string(block["today"], f"{name}.today")
    _require_non_empty_string(block["summary"], f"{name}.summary")

    for field in ("selloff", "defensive"):
        items = block[field]
        if not isinstance(items, list) or not 2 <= len(items) <= 3:
            raise ValueError(f"{name}.{field} must contain 2-3 items")
        for index, item in enumerate(items, start=1):
            _require_non_empty_string(item, f"{name}.{field}[{index}]")


def validate_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    _require_keys(payload, REQUIRED_TOP_LEVEL_KEYS, "payload")
    _require_non_empty_string(payload["date"], "date")
    _require_non_empty_string(payload["coverage"], "coverage")

    risk_mode = _require_non_empty_string(payload["risk_mode"], "risk_mode")
    if risk_mode not in {"Macro risk-off", "Macro risk-on"}:
        raise ValueError("risk_mode must be 'Macro risk-off' or 'Macro risk-on'")

    sources = payload["sources"]
    if not isinstance(sources, list) or len(sources) < 2:
        raise ValueError("sources must contain at least 2 items")
    for index, source in enumerate(sources, start=1):
        _require_non_empty_string(source, f"sources[{index}]")

    _require_non_empty_string(payload["key_takeaway"], "key_takeaway")

    indexes = payload["indexes"]
    if not isinstance(indexes, list) or len(indexes) != 5:
        raise ValueError("indexes must contain exactly 5 items")
    names = []
    for index, item in enumerate(indexes, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"indexes[{index}] must be an object")
        _require_keys(item, {"name", "level", "change", "view"}, f"indexes[{index}]")
        names.append(_require_non_empty_string(item["name"], f"indexes[{index}].name"))
        _require_non_empty_string(item["level"], f"indexes[{index}].level")
        _require_non_empty_string(item["change"], f"indexes[{index}].change")
        _require_non_empty_string(item["view"], f"indexes[{index}].view")
    if names != EXPECTED_INDEX_ORDER:
        raise ValueError(
            "indexes must follow the fixed order: " + ", ".join(EXPECTED_INDEX_ORDER)
        )

    _validate_market_block("a_share", payload["a_share"])
    _validate_market_block("h_share", payload["h_share"])

    news = payload["news"]
    if not isinstance(news, list) or len(news) < 3:
        raise ValueError("news must contain at least 3 items")
    categories = set()
    for index, item in enumerate(news, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"news[{index}] must be an object")
        _require_keys(
            item,
            {"category", "tag", "title", "explanation", "impact"},
            f"news[{index}]",
        )
        category = _require_non_empty_string(item["category"], f"news[{index}].category")
        tag = _require_non_empty_string(item["tag"], f"news[{index}].tag")
        if tag not in VALID_NEWS_TAGS:
            raise ValueError(
                f"news[{index}].tag must be one of: {', '.join(sorted(VALID_NEWS_TAGS))}"
            )
        _require_non_empty_string(item["title"], f"news[{index}].title")
        _require_non_empty_string(item["explanation"], f"news[{index}].explanation")
        _require_non_empty_string(item["impact"], f"news[{index}].impact")
        categories.add(category)

    missing_categories = REQUIRED_NEWS_CATEGORIES - categories
    if missing_categories:
        raise ValueError(
            "news categories must cover: "
            + ", ".join(sorted(REQUIRED_NEWS_CATEGORIES))
            + f"; missing: {', '.join(sorted(missing_categories))}"
        )

    strategy = payload["strategy"]
    if not isinstance(strategy, dict):
        raise ValueError("strategy must be an object")
    _require_keys(strategy, {"nature", "action"}, "strategy")
    _require_non_empty_string(strategy["nature"], "strategy.nature")
    _require_non_empty_string(strategy["action"], "strategy.action")

    tomorrow_watch = payload["tomorrow_watch"]
    if not isinstance(tomorrow_watch, list) or len(tomorrow_watch) != 3:
        raise ValueError("tomorrow_watch must contain exactly 3 items")
    for index, item in enumerate(tomorrow_watch, start=1):
        _require_non_empty_string(item, f"tomorrow_watch[{index}]")

    _require_non_empty_string(payload["data_note"], "data_note")
    return payload


def _render_market_block(title: str, block: dict) -> list[str]:
    summary_label = "A股" if "A股" in title else "港股"
    lines = [
        f"### {title}",
        "",
        "#### 今日走势",
        block["today"].strip(),
        "",
        "#### 杀跌方向",
    ]
    lines.extend(f"- {item.strip()}" for item in block["selloff"])
    lines.extend(
        [
            "",
            "#### 相对抗跌",
        ]
    )
    lines.extend(f"- {item.strip()}" for item in block["defensive"])
    lines.extend(
        [
            "",
            f"**{summary_label}一句话：{block['summary'].strip()}**",
            "",
        ]
    )
    return lines


def render_markdown(payload: object) -> str:
    note = validate_payload(payload)
    sources = " / ".join(item.strip() for item in note["sources"])

    lines = [
        "| DAILY STRATEGY NOTE \\| A/H EQUITIES | " + note["risk_mode"].strip() + " |",
        "| --- | ---: |",
        "",
        "# A股 & 港股 日度策略简报",
        "",
        f"**{note['date'].strip()} | {note['coverage'].strip()}**",
        "",
        f"数据来源：{sources}",
        "",
        "## 核心观点",
        "",
        "| Badge | Summary |",
        "| --- | --- |",
        f"| **核心** | {note['key_takeaway'].strip()} |",
        "",
        "## 主要指数收盘概览",
        "",
        "| 指数 | 点位 | 涨跌幅 | 判断 |",
        "| --- | ---: | ---: | --- |",
    ]

    for item in note["indexes"]:
        lines.append(
            f"| {item['name'].strip()} | {item['level'].strip()} | "
            f"{item['change'].strip()} | {item['view'].strip()} |"
        )

    lines.extend(
        [
            "",
            "## 双栏结构（核心分析区）",
            "",
        ]
    )
    lines.extend(_render_market_block("左栏 | A股观察", note["a_share"]))
    lines.extend(_render_market_block("右栏 | 港股观察", note["h_share"]))

    lines.extend(
        [
            "## 头条新闻与核心驱动",
            "",
        ]
    )

    for item in note["news"]:
        lines.append(f"- 【{item['tag'].strip()}】{item['title'].strip()}")
        lines.append(f"  → {item['explanation'].strip()}")
        lines.append(f"  → {item['impact'].strip()}")
        lines.append("")

    lines.extend(
        [
            "## 策略",
            "",
            f"- 性质：{note['strategy']['nature'].strip()}",
            f"- 应对：{note['strategy']['action'].strip()}",
            "",
            "## 明日观察",
            "",
        ]
    )
    lines.extend(f"- {item.strip()}" for item in note["tomorrow_watch"])
    lines.extend(
        [
            "",
            "## FOOTER",
            "",
            f"数据口径说明：{note['data_note'].strip()}",
            "",
            f"Sources：{sources}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a one-page A/H daily strategy note from structured JSON."
    )
    parser.add_argument("--input", required=True, help="Path to the JSON payload.")
    parser.add_argument(
        "--output",
        help="Optional output Markdown path. Defaults to stdout when omitted.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    markdown = render_markdown(payload)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
