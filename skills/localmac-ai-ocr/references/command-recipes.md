# Localmac AI OCR 命令配方

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
- 创建 `scripts/.venv`
- 安装 `requirements.txt`
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
- 或先 `gui capture` 更小区域
- 或用 `ocr annotate` 看看框是否正确

## 截图后按文字点击

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" "$SKILL_DIR/scripts/ocr" click-text /tmp/rdp.png --query 买入 --mode exact
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
