---
name: ah-daily-strategy-note
description: Use when 需要生成 A股/港股/ A/H equities 的日度策略简报、一页 PDF 券商风格策略页、收盘复盘加盘后线索摘要，并要求强结构、结论先行、可直接排版的卖方投行式输出。
metadata:
  openclaw:
    requires:
      bins:
        - python3
---

# A/H Daily Strategy Note

## 概览

这个 skill 用来生成单页卖方策略简报，默认口径是“收盘复盘 + 盘后线索”。
目标不是写新闻合集，而是产出可以直接贴进 PDF 版式的一页策略页。

先回答三个问题，再落文案：

1. 今天市场本质是什么
2. 这是系统性还是结构性变化
3. 明天最关键的交易变量是什么

## 何时使用

- 用户要 A股、港股、A/H、恒生科技、日度策略简报、盘后复盘、一页策略页
- 用户明确要求卖方投行、券商研报、信息设计、强结构排版
- 用户要“短句 + 判断 + 因果”，而不是长篇新闻综述

不要优先用于这些场景：

- 多页深度专题或行业白皮书
- 纯资讯播报，不需要策略判断
- 只需口头摘要，不需要可直接排版的 Markdown 成稿

## 前置依赖

- 涉及“今天 / 最新 / 收盘 / 盘后”时，先确认真实交易日期与收盘口径
- 必须覆盖上证、深证、创业板、恒生、恒生科技五个指数
- 必须覆盖宏观、政策、盘后变量三类驱动
- 每一条都要带因果，不要只复述涨跌或新闻标题

## 标准工作流

### 1. 先确认日期与口径

- 默认按用户指定交易日输出“收盘复盘 + 盘后线索”
- 若用户混淆“今天 / 明天 / 盘后”，在正文直接写绝对日期

### 2. 先做信息分层，不要直接成文

- 第一层：市场本质判断
- 第二层：指数与 A/H 差异
- 第三层：新闻驱动与明日变量

### 3. 先整理成结构化输入

优先按 [references/report_schema.md](references/report_schema.md) 组织字段，再生成最终 Markdown。

最低要求：

- 指数判断必须是结论，不是复述收盘数字
- A股与港股都要写“为什么杀跌”与“为什么抗跌”
- 港股部分要显式体现更敏感、beta 更高、与 A股的差异
- 新闻块每条都写“解释 + 影响”

### 4. 需要稳定版式时，优先走渲染脚本

从 skill 根目录执行：

```bash
python3 scripts/render_strategy_note.py --input /tmp/ah-note.json --output /tmp/ah-note.md
```

若需要直接生成券商风格 PDF，可使用 ReportLab 渲染器：

```bash
python3 scripts/render_strategy_note_reportlab.py \
  --input-markdown /tmp/ah-note.md \
  --output-pdf /tmp/ah-note.pdf \
  --hot-stocks-json /tmp/ah-hot-stocks.json
```

脚本会校验：

- 五个指数是否齐全且顺序正确
- 新闻是否覆盖宏观、政策、盘后变量
- 明日观察是否正好 3 条
- A股/港股的强弱方向是否各 2-3 条

### 5. 输出纪律

- 短句优先
- 结论前置
- 每条都写因果
- 多用“说明 / 意味着 / 反映 / 本质是”
- 避免“市场波动较大”“情绪偏弱”等空话

## 快速命令

- 生成 Markdown：

```bash
python3 scripts/render_strategy_note.py --input /tmp/ah-note.json
```

- 生成并写入文件：

```bash
python3 scripts/render_strategy_note.py --input /tmp/ah-note.json --output /tmp/ah-note.md
```

- 由 Markdown 直接生成 PDF：

```bash
python3 skills/ah-daily-strategy-note/scripts/render_strategy_note_reportlab.py \
  --input-markdown /tmp/ah-note.md \
  --output-pdf /tmp/ah-note.pdf \
  --hot-stocks-json /tmp/ah-hot-stocks.json
```

- 运行最小验证：

```bash
python3 skills/ah-daily-strategy-note/tests/test_render_strategy_note.py
```

## 常见风险

- 把报告写成新闻串烧，缺少“市场本质”判断
- A股与港股写成同一套逻辑，没有体现港股更高 beta
- 指数点评只复述涨跌，没有结论
- “明日观察”写成口号，而不是可验证变量
- 新闻只有解释，没有影响推演

## 参考文件

- `references/report_schema.md`
- `scripts/render_strategy_note.py`
