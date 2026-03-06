---
name: localmac-ai-ocr
description: Use when 需要在 macOS 本机或 RDP 场景下抓屏、识别中文界面文字与坐标、按文字定位并点击界面，尤其适合远程桌面窗口、行情软件、自选列表、按钮输入框定位和截图取字。
---

# Localmac AI OCR

## 概览

这个 skill 用来协同两个现成命令行工具：
- `gui` 负责窗口激活、截图、坐标点击、键盘输入
- `ocr` 负责调用 AI Studio OCR 输出文字、分数、坐标框，并支持按文本查找和点击

优先使用云端 `aistudio-ocr`。除非用户明确要求，不要回退到本地 Paddle，以免慢且占用内存。

不要把真实的 `API key`、`token`、`api url` 写进 skill、脚本调用示例或仓库文件。统一要求从环境变量或命令参数读取。

## 何时使用

- 用户要你操作本机 GUI、RDP 窗口或桌面 App
- 需要从截图中提取中文文本和坐标框
- 需要“先截图，再识别，再按文字点击”
- 需要验证 OCR 速度、完整输出、命中框、标注图
- 需要在行情软件、表格界面、按钮密集界面里精确找字

不要在这些场景优先使用网页抓取或 DOM 自动化；先判断是不是桌面/RDP 界面。

## 工作流

### 1. 先确认命令入口

优先使用当前工作区里的 `ocr` 和 `gui`。如果当前工作区就是 `localmac`，可直接使用：

```bash
/Users/weiwang/Projects/localmac/ocr
/Users/weiwang/Projects/localmac/gui
```

如果命令不在当前目录，先用 `pwd`、`ls` 或 `rg --files` 找到实际路径，再继续。

### 2. 先做环境体检

先确认 OCR token 和 GUI 依赖，再做截图或点击：

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr doctor
/Users/weiwang/Projects/localmac/gui doctor --json
```

若用户没有显式提供 token，先检查环境变量 `AISTUDIO_OCR_TOKEN` 是否已存在。
若用户使用自定义网关地址，只能通过环境变量或 `--aistudio-api-url` 传入；不要在 skill 里写死 URL。

### 3. GUI 场景先定位窗口再截图

标准顺序：

```bash
/Users/weiwang/Projects/localmac/gui list-windows
/Users/weiwang/Projects/localmac/gui activate --title 打新股
/Users/weiwang/Projects/localmac/gui capture /tmp/rdp.png --rect 0,30,2243,1266
```

规则：
- 先 `list-windows`，再 `activate`
- 截图优先落到 `/tmp`
- 已知区域就传 `--rect`，不确定时先全图截图再裁切

### 4. OCR 优先用 `ocr`，`gui ocr` 只做轻量探测

完整坐标、查找、点击、测速都走 `ocr`：

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr ocr /tmp/rdp.png --format json
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr find /tmp/rdp.png --query 腾讯控股 --mode contains --center --format json
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr click-text /tmp/rdp.png --query 腾讯控股 --mode contains
```

只需要快速看文字时，可用：

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/gui ocr /tmp/rdp.png --format text
```

### 5. 点击前先看命中框

不要盲点。默认先走这个顺序：

1. `ocr find --format json --center`
2. 检查命中数量、文字是否歧义
3. 必要时加 `--first`、`--mode exact` 或缩小截图范围
4. 再执行 `click-text` 或 `gui click`

如果界面中同名文本很多，先裁图再识别，不要直接点击全屏第一个命中项。

## 快速命令

- 完整 OCR JSON：
```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr ocr /tmp/rdp.png --format json
```

- 只看纯文本：
```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr ocr /tmp/rdp.png --format text
```

- 查文字并输出中心点：
```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr find /tmp/rdp.png --query 00700 --mode exact --center --format json
```

- 对识别结果打框：
```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr annotate /tmp/rdp.png /tmp/rdp-annotated.png --query 腾讯控股
```

- 测 10 次速度：
```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" /Users/weiwang/Projects/localmac/ocr benchmark /tmp/rdp.png --backend aistudio-ocr --repeat 10
```

## 常见失误

- 没激活窗口就截图，导致抓到旧画面
- 没传 `AISTUDIO_OCR_TOKEN`，结果自动回退到本地后端
- 命中文本太多却直接 `click-text`
- 对整个桌面做 OCR，导致慢且歧义多；应先裁切到目标区域
- 已有弹窗遮挡却继续点坐标，导致操作跑偏

## 参考

- 常见命令配方见 `references/command-recipes.md`
- 如果任务是“截图 -> 找字 -> 点击”，优先按参考里的 RDP 配方执行
- 如需自定义云端接口地址，只引用变量名，不写真实值
