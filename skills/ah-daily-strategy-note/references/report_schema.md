# Report Schema

这个 reference 只定义结构，不解释市场内容。

## 输出顺序

最终 Markdown 必须按下面顺序输出：

1. `HEADER`
2. `核心观点`
3. `主要指数收盘概览`
4. `双栏结构（核心分析区）`
5. `头条新闻与核心驱动`
6. `策略`
7. `明日观察`
8. `FOOTER`

## JSON 输入结构

```json
{
  "date": "2026-03-24",
  "coverage": "收盘复盘 + 盘后线索",
  "risk_mode": "Macro risk-off",
  "sources": ["Investing", "Reuters", "WSJ"],
  "key_takeaway": "今天市场本质是风险偏好压缩，但并非全面失速。A股更偏结构性杀估值，港股则放大外部风险冲击，反映资金先降 beta 再找防御。明天关键变量是外资流向与高 beta 板块是否出现修复。",
  "indexes": [
    {
      "name": "上证",
      "level": "3,120.44",
      "change": "-0.36%",
      "view": "权重托底弱化，说明指数稳定性开始依赖防御板块。"
    }
  ],
  "a_share": {
    "today": "A股缩量回落，说明资金更偏向内部切换而非全面撤退。",
    "selloff": [
      "成长赛道回撤，原因是风险偏好下降后，高估值先被压缩。"
    ],
    "defensive": [
      "高股息继续抗跌，反映资金仍在用现金流确定性对冲波动。"
    ],
    "summary": "A股本质是存量博弈下的结构性降风险。"
  },
  "h_share": {
    "today": "港股跌幅更深，说明外部利率与地缘因子对 beta 资产的压制更直接。",
    "selloff": [
      "平台与可选消费承压，原因是海外风险因子先打估值再打预期。"
    ],
    "defensive": [
      "电信与高股息相对抗跌，反映避险资金优先回到低波动现金流资产。"
    ],
    "summary": "港股本质是外部定价变量触发的高 beta 回撤。"
  },
  "news": [
    {
      "category": "宏观",
      "tag": "利空",
      "title": "美债收益率走高",
      "explanation": "无风险利率上行压缩成长资产估值。",
      "impact": "意味着港股高 beta 板块对外部扰动更敏感。"
    },
    {
      "category": "政策",
      "tag": "中性",
      "title": "政策表态延续稳增长",
      "explanation": "增量政策预期仍在，但短期缺乏更强催化。",
      "impact": "说明 A股更多体现为板块轮动，而非指数级别趋势反转。"
    },
    {
      "category": "盘后变量",
      "tag": "盘后",
      "title": "龙头公司盘后披露经营更新",
      "explanation": "盘后信息会影响次日风格偏好与风险容忍度。",
      "impact": "意味着明早资金会优先验证业绩和指引是否支撑修复。"
    }
  ],
  "strategy": {
    "nature": "今天更偏结构性降风险，不是系统性流动性踩踏。",
    "action": "短线以观察 beta 修复质量为主，配置上继续偏现金流与政策确定性。"
  },
  "tomorrow_watch": [
    "外资是否回流",
    "高 beta 板块是否出现修复",
    "油价与美债收益率是否回落"
  ],
  "data_note": "指数表现按对应市场收盘口径统计，新闻纳入盘后公开信息。"
}
```

## 字段约束

- `risk_mode` 只写 `Macro risk-off` 或 `Macro risk-on`
- `sources` 至少 2 个，按 `Investing / Reuters / WSJ` 这种格式展示
- `indexes` 必须正好 5 个，顺序固定为：
  - 上证
  - 深证
  - 创业板
  - 恒生
  - 恒生科技
- `a_share.selloff`、`a_share.defensive`、`h_share.selloff`、`h_share.defensive` 都必须是 2-3 条
- `news` 至少 3 条，且 `category` 必须覆盖：
  - 宏观
  - 政策
  - 盘后变量
- `news.tag` 只允许：
  - 利空
  - 利好
  - 中性
  - 盘后
- `tomorrow_watch` 必须正好 3 条，且每条都必须是“变量”

## 写作纪律

- 不写空话
- 不重复同一个结论
- 每一条都要有因果
- 多用“说明 / 意味着 / 反映 / 本质是”
- “一句话总结”必须是压缩后的判断，不是重复前文
