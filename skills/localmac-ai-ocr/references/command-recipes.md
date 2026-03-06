# Localmac AI OCR 命令配方

## Agent Quick Recipe

给 agent 的最短稳定流程：

1. 截图到 `/tmp`
2. 用 `ocr find --center --format json --annotate-output` 找目标文字
3. 看命中数量
4. 单命中就 `click-text --index 1`
5. 多命中就改 `--mode exact`、补 `--index N`，或缩小截图范围
6. 点击后再截图核验

整屏点击模板：

```bash
"$SKILL_DIR/scripts/gui" capture /tmp/current.png
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/current.png --query 自动化 --mode contains --center --format json --annotate-output /tmp/current-annotated.png
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/current.png --query 自动化 --mode contains --index 1
"$SKILL_DIR/scripts/gui" capture /tmp/after-click.png
```

局部截图点击模板：

```bash
"$SKILL_DIR/scripts/gui" capture /tmp/region.png --rect 100,200,800,600
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/region.png --query 买入 --mode exact --center --format json --annotate-output /tmp/region-annotated.png
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/region.png --query 买入 --mode exact --index 1 --screen-rect "100,200,800,600"
```

要点：

- Retina 屏会自动把截图像素坐标换算成屏幕 point
- 不要在多命中时盲点，优先用 `--index N`
- 需要给人或 agent 复核时，始终加 `--annotate-output`

## 环境变量

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
export AISTUDIO_OCR_TOKEN='你的 token'
export AISTUDIO_OCR_API_URL='你的 OCR 接口地址'
```

说明：
- `AISTUDIO_OCR_TOKEN` 和 `AISTUDIO_OCR_API_URL` 都属于运行时配置，不能写死进 skill 或提交到仓库
- 如果用户只要求云端 OCR，不要默认切回本地 Paddle

## 首次安装依赖

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr"
"$SKILL_DIR/scripts/setup.sh"
```

`setup.sh` 会：
- 用 `uv sync` 安装 `pyproject.toml` 里的依赖
- 如果不存在 `scripts/.env`，自动从 `.env.example` 复制一份模板

## 配置 API

推荐直接编辑：

```bash
$SKILL_DIR/scripts/.env
```

必填项：
- `AISTUDIO_OCR_API_URL`
- `AISTUDIO_OCR_TOKEN`

排障时只检查“是否已配置”，不要在终端回显真实值。

## RDP/桌面 App 标准配方

```bash
"$SKILL_DIR/scripts/gui" list-windows
"$SKILL_DIR/scripts/gui" activate --title 打新股
"$SKILL_DIR/scripts/gui" capture /tmp/rdp.png --rect 0,30,2243,1266
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/rdp.png --query 腾讯控股 --mode contains --center --format json
```

如果命中结果超过 1 个：
- 先改成 `--mode exact`
- 或显式传 `--index N`
- 或先 `gui capture` 更小区域
- 或用 `ocr annotate` 看看框是否正确

## 截图后按文字点击

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/rdp.png --query 买入 --mode exact
```

如果同一张图里有多个同名文本，直接指定第几个：

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/rdp.png --query 自动化 --mode contains --index 2
```

更稳的方式：

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" find /tmp/rdp.png --query 买入 --mode exact --center --format json
"$SKILL_DIR/scripts/gui" click 1200 700
```

适合这些情况：
- 同一截图要重复点击多个目标
- 需要把坐标记录到日志里
- 要先人工确认框

## 取完整 JSON

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" ocr /tmp/rdp.png --format json > /tmp/ocr.json
```

返回重点字段通常包括：
- `text`
- `score`
- `bbox`
- `quad`

如果需要一边拿 JSON 一边产出给 agent 复核的标注图：

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" ocr /tmp/rdp.png --format json --annotate-output /tmp/ocr-annotated.png > /tmp/ocr.json
```

标注图默认会在每个框上方显示：
- 识别文本
- 中心坐标 `center=(x,y)`
- 置信度 `score=...`

常用标注控制参数：
- `--annotate-no-text` 只看坐标和分数
- `--annotate-no-center` 不显示中心坐标
- `--annotate-no-score` 不显示置信度
- `--annotate-color '#16a34a'` 调整框和标签颜色

## 标注与裁图

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" annotate /tmp/rdp.png /tmp/annotated.png --query 腾讯控股
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" crop-matches /tmp/rdp.png /tmp/crops --query 腾讯控股
```

## 性能测试

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" benchmark /tmp/rdp.png --backend aistudio-ocr --repeat 10
```

先用一张固定测试图比较，再换真实业务截图；不要把不同尺寸的图混在一起比较耗时。

## 排障

- `ocr doctor` 看 OCR 配置状态
- `gui doctor --json` 看 GUI 权限和依赖
- 截图不对时，先重新 `activate`
- 点击跑偏时，先用 `find --center --format json` 检查坐标是否来自当前截图
- 多命中时，优先用 `--index N` 指定第几个命中项，而不是依赖模糊匹配
- 如果是区域截图，点击前补 `--screen-rect "x,y,width,height"`，让截图坐标能正确映射回屏幕 point
- 如果需要和人或 agent 一起复核，优先加 `--annotate-output` 输出带坐标与置信度的标注图
