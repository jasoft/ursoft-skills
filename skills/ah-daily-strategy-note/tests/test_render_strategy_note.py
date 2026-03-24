from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_strategy_note


SAMPLE_PAYLOAD = {
    "date": "2026-03-24",
    "coverage": "收盘复盘 + 盘后线索",
    "risk_mode": "Macro risk-off",
    "sources": ["Investing", "Reuters", "WSJ"],
    "key_takeaway": (
        "今天市场本质是风险偏好压缩，但并非全面失速。"
        "A股更偏结构性杀估值，港股则放大外部风险冲击，反映资金先降 beta 再找防御。"
        "明天关键变量是外资流向与高 beta 板块是否出现修复。"
    ),
    "indexes": [
        {
            "name": "上证",
            "level": "3,120.44",
            "change": "-0.36%",
            "view": "权重托底弱化，说明指数稳定性开始依赖防御板块。",
        },
        {
            "name": "深证",
            "level": "9,812.73",
            "change": "-0.88%",
            "view": "中盘成长回撤更深，反映风险偏好先打成长估值。",
        },
        {
            "name": "创业板",
            "level": "1,925.18",
            "change": "-1.24%",
            "view": "高弹性板块领跌，意味着资金没有急于做 beta 修复。",
        },
        {
            "name": "恒生",
            "level": "16,488.51",
            "change": "-1.62%",
            "view": "港股跌幅放大，说明外部定价因子主导情绪。",
        },
        {
            "name": "恒生科技",
            "level": "3,412.06",
            "change": "-2.41%",
            "view": "科技成长承压更重，反映高 beta 资产先被减仓。",
        },
    ],
    "a_share": {
        "today": "A股缩量回落，说明资金更偏向内部切换而非全面撤退。",
        "selloff": [
            "成长赛道回撤，原因是风险偏好下降后，高估值先被压缩。",
            "券商链条走弱，反映交易热度不足时高弹性金融先失去增量资金。",
        ],
        "defensive": [
            "高股息继续抗跌，反映资金仍在用现金流确定性对冲波动。",
            "公用事业相对稳定，说明避险仓位并未离场。",
        ],
        "summary": "A股本质是存量博弈下的结构性降风险。",
    },
    "h_share": {
        "today": "港股跌幅更深，说明外部利率与地缘因子对 beta 资产的压制更直接。",
        "selloff": [
            "平台与可选消费承压，原因是海外风险因子先打估值再打预期。",
            "互联网龙头回撤更快，反映港股对全球资金再定价更敏感。",
        ],
        "defensive": [
            "电信与高股息相对抗跌，反映避险资金优先回到低波动现金流资产。",
            "能源板块跌幅较小，说明资源属性仍在提供阶段性缓冲。",
        ],
        "summary": "港股本质是外部定价变量触发的高 beta 回撤。",
    },
    "news": [
        {
            "category": "宏观",
            "tag": "利空",
            "title": "美债收益率走高",
            "explanation": "无风险利率上行压缩成长资产估值。",
            "impact": "意味着港股高 beta 板块对外部扰动更敏感。",
        },
        {
            "category": "政策",
            "tag": "中性",
            "title": "政策表态延续稳增长",
            "explanation": "增量政策预期仍在，但短期缺乏更强催化。",
            "impact": "说明 A股更多体现为板块轮动，而非指数级别趋势反转。",
        },
        {
            "category": "盘后变量",
            "tag": "盘后",
            "title": "龙头公司盘后披露经营更新",
            "explanation": "盘后信息会影响次日风格偏好与风险容忍度。",
            "impact": "意味着明早资金会优先验证业绩和指引是否支撑修复。",
        },
    ],
    "strategy": {
        "nature": "今天更偏结构性降风险，不是系统性流动性踩踏。",
        "action": "短线以观察 beta 修复质量为主，配置上继续偏现金流与政策确定性。",
    },
    "tomorrow_watch": [
        "外资是否回流",
        "高 beta 板块是否出现修复",
        "油价与美债收益率是否回落",
    ],
    "data_note": "指数表现按对应市场收盘口径统计，新闻纳入盘后公开信息。",
}


class RenderStrategyNoteTests(unittest.TestCase):
    def test_render_markdown_contains_required_sections_in_order(self) -> None:
        markdown = render_strategy_note.render_markdown(SAMPLE_PAYLOAD)

        self.assertIn("| DAILY STRATEGY NOTE \\| A/H EQUITIES | Macro risk-off |", markdown)
        self.assertIn("# A股 & 港股 日度策略简报", markdown)
        self.assertIn("## 主要指数收盘概览", markdown)
        self.assertIn("### 左栏 | A股观察", markdown)
        self.assertIn("### 右栏 | 港股观察", markdown)
        self.assertIn("## 头条新闻与核心驱动", markdown)
        self.assertIn("## FOOTER", markdown)

        self.assertLess(markdown.index("## 核心观点"), markdown.index("## 主要指数收盘概览"))
        self.assertLess(markdown.index("## 主要指数收盘概览"), markdown.index("## 双栏结构（核心分析区）"))
        self.assertLess(markdown.index("## 双栏结构（核心分析区）"), markdown.index("## 头条新闻与核心驱动"))
        self.assertIn("**A股一句话：A股本质是存量博弈下的结构性降风险。**", markdown)
        self.assertIn("**港股一句话：港股本质是外部定价变量触发的高 beta 回撤。**", markdown)

    def test_validate_payload_rejects_missing_news_categories(self) -> None:
        payload = copy.deepcopy(SAMPLE_PAYLOAD)
        payload["news"] = payload["news"][:2]

        with self.assertRaises(ValueError) as ctx:
            render_strategy_note.validate_payload(payload)

        self.assertIn("news must contain at least 3 items", str(ctx.exception))

    def test_validate_payload_rejects_wrong_index_order(self) -> None:
        payload = copy.deepcopy(SAMPLE_PAYLOAD)
        payload["indexes"][0], payload["indexes"][1] = (
            payload["indexes"][1],
            payload["indexes"][0],
        )

        with self.assertRaises(ValueError) as ctx:
            render_strategy_note.validate_payload(payload)

        self.assertIn("fixed order", str(ctx.exception))

    def test_main_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.json"
            output_path = Path(tmpdir) / "note.md"
            input_path.write_text(
                json.dumps(SAMPLE_PAYLOAD, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            exit_code = render_strategy_note.main(
                ["--input", str(input_path), "--output", str(output_path)]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            self.assertIn("数据口径说明", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
