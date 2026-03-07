# WeChat Send 与 localmac-ai-ocr 的整合方式

## 目标

让 `wechat-send` 在任意机器上都能工作，同时把 GUI / OCR 能力复用给 `localmac-ai-ocr`，避免：

- 硬编码 `/Users/...` 这类绝对目录
- 直接 import 另一个 skill 的 Python 模块
- 依赖另一个 skill 的 `.venv/bin/python`

## 推荐做法

`wechat-send` 只把 `localmac-ai-ocr` 当成一个提供公共 CLI 的依赖 skill，调用下面两个稳定入口：

```bash
localmac-ai-ocr/scripts/gui
localmac-ai-ocr/scripts/ocr
```

目录发现顺序建议固定成：

1. 命令行参数 `--ocr-skill-dir`
2. 环境变量 `LOCALMAC_AI_OCR_DIR`
3. 当前 skill 的同级目录 `../localmac-ai-ocr`
4. `${CODEX_HOME:-$HOME/.codex}/skills/localmac-ai-ocr`
5. `${HOME}/.agents/skills/localmac-ai-ocr`

只要找到同时包含 `scripts/gui` 和 `scripts/ocr` 的目录，就认为依赖可用。

## 为什么不要直接 import

如果 `wechat-send` 直接 import `localmac-ai-ocr/scripts/ocr_tool.py`，会带来几个问题：

- 两边的 Python 运行时耦合
- 对方调整包结构后这里会直接坏掉
- 对方改成 `uv run`、改依赖管理方式后，这边也要跟着改

CLI 契约更稳，因为调用者只关心“能执行什么命令”，不关心内部怎么实现。

## 建议的职责边界

`wechat-send` 负责：

- 激活微信
- 搜索联系人
- 粘贴消息
- 在业务节点决定是否需要截图或 OCR 校验

`localmac-ai-ocr` 负责：

- 截图
- OCR 识别
- 文字定位
- 坐标点击

## 调用示例

截图核验：

```bash
"$LOCALMAC_AI_OCR_DIR/scripts/gui" capture /tmp/wechat-current.png
```

查找联系人文本：

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" \
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" \
"$LOCALMAC_AI_OCR_DIR/scripts/ocr" find /tmp/wechat-current.png --query 文件传输助手 --mode contains --center --format json
```

按文字点击：

```bash
AISTUDIO_OCR_API_URL="$AISTUDIO_OCR_API_URL" \
AISTUDIO_OCR_TOKEN="$AISTUDIO_OCR_TOKEN" \
"$LOCALMAC_AI_OCR_DIR/scripts/ocr" click-text /tmp/wechat-current.png --query 文件传输助手 --mode contains --index 1
```

## 如果以后要继续演进

如果大王后面想把整合做得更规范，小的建议按这个方向：

1. 给 `localmac-ai-ocr` 明确定义公共命令契约，只在 `SKILL.md` 写 `gui` 和 `ocr` 的稳定子命令
2. 给 `wechat-send` 继续补 `capture-before-send`、`verify-contact` 这类编排能力
3. 让跨 skill 依赖统一走 `SKILL_DIR` 发现逻辑或环境变量，而不是每个 skill 自己乱猜路径
