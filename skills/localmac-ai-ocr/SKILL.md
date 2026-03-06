---
name: localmac-ai-ocr
description: Use when 需要在 macOS 本机或 RDP 场景下抓屏、识别中文界面文字与坐标、按文字定位并点击界面，尤其适合远程桌面窗口、行情软件、自选列表、按钮输入框定位和截图取字。
metadata:
    openclaw:
        requires:
            env:
                - AISTUDIO_OCR_TOKEN
                - AISTUDIO_OCR_API_URL
            bins:
                - python3
                - osascript
                - /usr/sbin/screencapture
                - sips
---

# Localmac AI OCR

## 概览

这个 skill 用来协同两个现成命令行工具：

- `scripts/gui` 负责窗口激活、截图、坐标点击、键盘输入
- `scripts/ocr` 负责调用 AI Studio OCR 输出文字、分数、坐标框，并支持按文本查找和点击

优先使用云端 `aistudio-ocr`。除非用户明确要求，不要回退到本地 Paddle，以免慢且占用内存。

不要把真实的 `API key`、`token`、`api url` 写进 skill、脚本调用示例或仓库文件。统一要求从环境变量或命令参数读取。

这个 skill 自带可执行脚本，安装后不依赖业务仓库本身。默认把 skill 目录记作：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
```

可执行入口在：

```bash
$SKILL_DIR/scripts/ocr
$SKILL_DIR/scripts/gui
```

首次安装建议运行：

```bash
"$SKILL_DIR/scripts/setup.sh"
```

## 何时使用

- 用户要你操作本机 GUI、RDP 窗口或桌面 App
- 需要从截图中提取中文文本和坐标框
- 需要“先截图，再识别，再按文字点击”
- 需要验证 OCR 速度、完整输出、命中框、标注图
- 需要在行情软件、表格界面、按钮密集界面里精确找字

不要在这些场景优先使用网页抓取或 DOM 自动化；先判断是不是桌面/RDP 界面。

## 工作流

### 1. 先确认命令入口

先确认 skill 已安装，再定位脚本入口：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
test -x "$SKILL_DIR/scripts/ocr"
test -x "$SKILL_DIR/scripts/gui"
```

如果用户把 skill 放在别的位置，可先用 `find` 或 `rg --files` 找到 `localmac-ai-ocr/scripts/ocr` 再继续。不要在 skill、提交内容或对外说明里暴露用户本地目录名。

### 2. 先安装最小依赖

推荐直接运行自带安装脚本：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
"$SKILL_DIR/scripts/setup.sh"
```

如果需要手动安装，再执行下面这些命令：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
cd "$SKILL_DIR/scripts"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### 3. 先配置必填项

这个 skill 的云端 OCR 有两个必填配置：

- `AISTUDIO_OCR_API_URL`
- `AISTUDIO_OCR_TOKEN`

推荐方式：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
cp "$SKILL_DIR/scripts/.env.example" "$SKILL_DIR/scripts/.env"
```

然后编辑 `scripts/.env`，填入真实值。不要把 `.env` 提交回仓库。

也可以临时用环境变量传入，但仍然不要把真实值写进脚本、skill 或提交记录。

### 4. 先做环境体检

先确认 OCR token 和 GUI 依赖，再做截图或点击：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" doctor
"$SKILL_DIR/scripts/gui" doctor --json
```

`doctor` 只看是否已配置，不应打印真实 `token` 或接口地址。

### 5. GUI 场景先定位窗口再截图

标准顺序：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
"$SKILL_DIR/scripts/gui" list-windows
"$SKILL_DIR/scripts/gui" activate --title 打新股
"$SKILL_DIR/scripts/gui" capture /tmp/rdp.png --rect 0,30,2243,1266
```

规则：

- 先 `list-windows`，再 `activate`
- 截图优先落到 `/tmp`
- 已知区域就传 `--rect`，不确定时先全图截图再裁切

### 6. OCR 优先用 `ocr`，`gui ocr` 只做轻量探测

完整坐标、查找、点击、测速都走 `ocr`：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" ocr /tmp/rdp.png --format json
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/rdp.png --query 腾讯控股 --mode contains --center --format json
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/rdp.png --query 腾讯控股 --mode contains
```

只需要快速看文字时，可用：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/gui" ocr /tmp/rdp.png --format text
```

### 7. 点击前先看命中框

不要盲点。默认先走这个顺序：

1. `ocr find --format json --center`
2. 检查命中数量、文字是否歧义
3. 必要时加 `--first`、`--mode exact` 或缩小截图范围
4. 再执行 `click-text` 或 `gui click`

如果界面中同名文本很多，先裁图再识别，不要直接点击全屏第一个命中项。

## 快速命令

- 完整 OCR JSON：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" ocr /tmp/rdp.png --format json
```

- 只看纯文本：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" ocr /tmp/rdp.png --format text
```

- 查文字并输出中心点：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/rdp.png --query 00700 --mode exact --center --format json
```

- 对识别结果打框：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" annotate /tmp/rdp.png /tmp/rdp-annotated.png --query 腾讯控股
```

- 测 10 次速度：

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" benchmark /tmp/rdp.png --backend aistudio-ocr --repeat 10
```

## 常见失误

- 没激活窗口就截图，导致抓到旧画面
- 没同时配置 `AISTUDIO_OCR_API_URL` 和 `AISTUDIO_OCR_TOKEN`
- 把真实配置写进仓库，而不是放进 `scripts/.env`
- 命中文本太多却直接 `click-text`
- 对整个桌面做 OCR，导致慢且歧义多；应先裁切到目标区域
- 已有弹窗遮挡却继续点坐标，导致操作跑偏

## 参考

- 常见命令配方见 `references/command-recipes.md`
- 可执行脚本位于 `scripts/`
- 如果任务是“截图 -> 找字 -> 点击”，优先按参考里的 RDP 配方执行
- 如需自定义云端接口地址，只引用变量名，不写真实值
