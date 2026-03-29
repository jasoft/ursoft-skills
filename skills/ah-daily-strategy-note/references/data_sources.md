# Data Sources

这个 reference 用来锁定 `ah-daily-strategy-note` 可用的数据来源池，并约束不同来源的使用边界。
目标不是把所有媒体混成同一权重，而是让模型知道：

1. 哪些适合拿行情与事实
2. 哪些适合拿解释与线索
3. 哪些只能作为情绪或观点补充

## 选源优先级

固定按下面顺序判断：

1. 官方披露 / 交易所 / 公司公告 / 政府原文
2. 专业终端与市场数据源
3. 专业财经媒体
4. 观点与策略平台

若出现冲突：

- 数字、披露时间、财报日程，以官方披露和交易所为准
- 行情、板块、个股涨跌，以市场数据源为准
- 宏观与政策解读，可用专业媒体补解释，但不要替代原始政策表述
- 观点平台不能单独支撑“事实性结论”

## 国内（深度 / 专业）

- 财新网：https://www.caixin.com
- 经济观察网：https://www.eeo.com.cn
- 财经网：https://www.caijing.com.cn
- 21世纪经济报道：https://www.21jingji.com
- 第一财经：https://www.yicai.com
- 界面新闻：https://www.jiemian.com
- 财联社：https://www.cls.cn
- 华尔街见闻：https://wallstreetcn.com

适用：

- 宏观事件解释
- 政策与监管口径跟踪
- 产业链与公司新闻线索
- 盘后市场情绪与卖方关注点

## 国内（数据 / 市场）

- 东方财富网：https://www.eastmoney.com
- 同花顺财经：https://www.10jqka.com.cn
- 金融界：https://www.jrj.com.cn
- 雪球：https://xueqiu.com

适用：

- 指数、板块、个股行情
- 市场横截面排名
- 热门股、资金偏好、盘口温度

注意：

- 雪球可用于补投资者讨论热度与市场关注点，不要单独作为硬事实来源

## 国际（核心专业媒体）

- Bloomberg：https://www.bloomberg.com
- Reuters：https://www.reuters.com
- Financial Times：https://www.ft.com
- Wall Street Journal：https://www.wsj.com

适用：

- 海外宏观
- 地缘政治
- 利率、汇率、商品与全球风险偏好
- 港股离岸估值压制因素

## 国际（宏观 / 研究）

- The Economist：https://www.economist.com
- Project Syndicate：https://www.project-syndicate.org
- IMF Blog：https://www.imf.org/en/Blogs

适用：

- 中长期宏观框架
- 政策讨论与研究视角

注意：

- 这类来源更适合补背景和解释，不适合充当“今天盘后主驱动”的唯一依据

## 投资 / 策略类

- Seeking Alpha：https://seekingalpha.com
- MarketWatch：https://www.marketwatch.com
- ZeroHedge：https://www.zerohedge.com

适用：

- 海外投资者关注点
- 情绪与叙事线索
- 市场讨论热点

注意：

- Seeking Alpha、ZeroHedge 只能作为观点补充，不能单独支撑关键事实判断
- MarketWatch 可用于补充行情叙事，但关键数字仍应交叉验证

## 专业终端（机构级）

- Bloomberg Terminal：https://www.bloomberg.com/professional
- Wind：https://www.wind.com.cn
- FactSet：https://www.factset.com

适用：

- 高质量行情、财报、估值与跨市场对照
- 机构级时间序列与事件日历

注意：

- 若终端可用，优先用作数字核验
- 若终端不可用，不要假设已经访问过，改用公开可验证来源

## 组合取材规则

- 生成简报时，`sources` 至少写 2 个，且最好同时覆盖：
  - 1 个市场数据源
  - 1 个新闻或政策源
- 涉及 A/H 收盘复盘时，最低建议组合：
  - 东方财富 / 同花顺 / Wind / FactSet 任选其一做行情底稿
  - 财联社 / 第一财经 / 路透 / Bloomberg 任选其一做新闻补充
  - 若写港股盘后变量，再补 HKEX 或公司公告
- 涉及宏观与政策时，尽量采用：
  - 官方原文 + 专业媒体解释
- 涉及高争议叙事时，至少双重验证，不要只信单一媒体 headline
