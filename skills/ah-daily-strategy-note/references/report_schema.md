# Report Schema

这个 reference 不再服务脚本渲染。
它是给 LLM 用的固定内容结构，用来保证每次输出都保持同样的卖方策略页逻辑。

## 固定输出顺序

最终 Markdown 必须按下面顺序输出：

1. `HEADER`
2. `核心观点`
3. `主要指数收盘概览`
4. `双栏结构（核心分析区）`
5. `市场微观动态`
6. `头条新闻与核心驱动`
7. `策略`
8. `明日观察`
9. `FOOTER`

## LLM 工作结构

生成前，先在脑中把信息整理成下面结构，再落正式 Markdown：

```json
{
  "date": "2026-03-24",
  "coverage": "收盘复盘 + 盘后线索",
  "risk_mode": "Macro risk-off",
  "sources": ["Eastmoney", "财联社", "HKEX"],
  "key_takeaway": "今天市场本质是什么、系统性还是结构性、明天关键变量是什么。",
  "indexes": [
    {
      "name": "上证",
      "level": "3,120.44",
      "change": "-0.36%",
      "view": "指数判断必须是结论，不是复述点位。"
    }
  ],
  "a_share": {
    "today": "A股今日走势的总判断。",
    "selloff": ["2-3条，写清因果。"],
    "defensive": ["2-3条，写清因果。"],
    "summary": "A股一句话判断。"
  },
  "h_share": {
    "today": "港股今日走势的总判断。",
    "selloff": ["2-3条，写清因果。"],
    "defensive": ["2-3条，写清因果。"],
    "summary": "港股一句话判断。"
  },
  "micro_dynamics": {
    "a_share_hot_stocks": [
      {
        "name": "热门股名称",
        "change": "+10.00%",
        "tag": "利好",
        "comment": "解释为什么涨，说明资金在交易什么。"
      }
    ],
    "h_share_hot_stocks": [
      {
        "name": "热门股名称",
        "change": "-3.20%",
        "tag": "利空",
        "comment": "解释为什么跌，说明离岸资金在定价什么。"
      }
    ],
    "leading_sectors": [
      {
        "name": "锂矿 / 医药 / 能源金属",
        "tag": "领涨",
        "comment": "写成板块 + 触发因子 + 市场含义。"
      }
    ],
    "lagging_sectors": [
      {
        "name": "风电 / 光伏 / 平台互联网",
        "tag": "领跌",
        "comment": "写成板块 + 压制因子 + 风险含义。"
      }
    ],
    "commodities": [
      {
        "name": "黄金",
        "change": "偏强 / 回落 / 高位震荡",
        "tag": "中性",
        "comment": "解释对风险偏好和资源链映射的含义。"
      },
      {
        "name": "白银",
        "change": "偏强 / 回落 / 高波动",
        "tag": "中性",
        "comment": "解释弹性和工业属性对市场的含义。"
      },
      {
        "name": "油价",
        "change": "上行 / 回落 / 高位震荡",
        "tag": "利空",
        "comment": "解释对港股估值、航运、资源和风险溢价的含义。"
      }
    ]
  },
  "news": [
    {
      "category": "宏观",
      "tag": "利空",
      "title": "标题",
      "explanation": "解释",
      "impact": "影响"
    }
  ],
  "strategy": {
    "nature": "今天行情的性质。",
    "action": "明天怎么应对。"
  },
  "tomorrow_watch": [
    "变量1",
    "变量2",
    "变量3"
  ],
  "data_note": "数据口径说明。"
}
```

## 字段约束

- `risk_mode` 只写 `Macro risk-off` 或 `Macro risk-on`
- `sources` 至少 2 个
- `indexes` 必须正好 5 个，顺序固定为：
  - 上证
  - 深证
  - 创业板
  - 恒生
  - 恒生科技
- `a_share.selloff`、`a_share.defensive`、`h_share.selloff`、`h_share.defensive` 都必须是 2-3 条
- `micro_dynamics.a_share_hot_stocks` 必须 2-4 条
- `micro_dynamics.h_share_hot_stocks` 必须 2-4 条
- `micro_dynamics.leading_sectors` 必须 2-4 条
- `micro_dynamics.lagging_sectors` 必须 2-4 条
- `micro_dynamics.commodities` 必须至少覆盖：
  - 黄金
  - 白银
  - 油价
- `tag` 允许使用：
  - 利好
  - 利空
  - 中性
  - 盘后
  - 暴涨
  - 暴跌
  - 抗跌
  - 领涨
  - 领跌
- `news` 至少 3 条，且必须覆盖：
  - 宏观
  - 政策
  - 盘后变量
- `tomorrow_watch` 必须正好 3 条

## 微观动态写法

- 热门股不能只写“谁涨了”，必须写“为什么被交易”
- 大涨股和大跌股都要尽量覆盖，至少让读者知道资金偏好和风险厌恶分别落在哪
- 板块要写“方向 + 因果 + 含义”
- 商品要写“方向 + 传导链”

好例子：

- `【利好】融捷股份 +10.00%：锂矿资源弹性被资金抢先定价，说明日内主线是上游资源而不是制造修复。`
- `【领跌】平台互联网：中美贸易 headline 再度压制离岸科技估值，说明港股高 beta 仍在打折。`
- `【利空】油价高位震荡：外部风险溢价没有完全出清，意味着港股成长估值修复空间仍受约束。`

坏例子：

- `融捷股份上涨。`
- `黄金价格波动。`
- `医药板块表现较好。`

## 写作纪律

- 不写空话
- 不重复同一个结论
- 每一条都要有因果
- 多用“说明 / 意味着 / 反映 / 本质是”
- “一句话总结”必须是压缩后的判断，不是重复前文
- 页面是策略页，不是资讯列表
