# Localmac AI OCR 命令配方

## 环境变量

```bash
export AISTUDIO_OCR_TOKEN='你的 token'
export AISTUDIO_OCR_API_URL='你的 OCR 接口地址'
```

说明：
- `AISTUDIO_OCR_TOKEN` 和 `AISTUDIO_OCR_API_URL` 都属于运行时配置，不能写死进 skill 或提交到仓库
- 如果接口地址使用默认值，可以只配置 `AISTUDIO_OCR_TOKEN`
- 如果用户只要求云端 OCR，不要默认切回本地 Paddle

## RDP/桌面 App 标准配方

```bash
./gui list-windows
./gui activate --title 打新股
./gui capture /tmp/rdp.png --rect 0,30,2243,1266
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr find /tmp/rdp.png --query 腾讯控股 --mode contains --center --format json
```

如果命中结果超过 1 个：
- 先改成 `--mode exact`
- 或先 `gui capture` 更小区域
- 或用 `ocr annotate` 看看框是否正确

## 截图后按文字点击

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr click-text /tmp/rdp.png --query 买入 --mode exact
```

更稳的方式：

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr find /tmp/rdp.png --query 买入 --mode exact --center --format json
./gui click 1200 700
```

适合这些情况：
- 同一截图要重复点击多个目标
- 需要把坐标记录到日志里
- 要先人工确认框

## 取完整 JSON

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr ocr /tmp/rdp.png --format json > /tmp/ocr.json
```

返回重点字段通常包括：
- `text`
- `score`
- `bbox`
- `quad`

## 标注与裁图

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr annotate /tmp/rdp.png /tmp/annotated.png --query 腾讯控股
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr crop-matches /tmp/rdp.png /tmp/crops --query 腾讯控股
```

## 性能测试

```bash
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" ./ocr benchmark /tmp/rdp.png --backend aistudio-ocr --repeat 10
```

先用一张固定测试图比较，再换真实业务截图；不要把不同尺寸的图混在一起比较耗时。

## 排障

- `ocr doctor` 看 OCR 配置状态
- `gui doctor --json` 看 GUI 权限和依赖
- 截图不对时，先重新 `activate`
- 点击跑偏时，先用 `find --center --format json` 检查坐标是否来自当前截图
