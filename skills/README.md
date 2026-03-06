# WeChat Auto Skill for OpenClaw

自动化 macOS 上微信消息发送的 OpenClaw skill。使用纯 UI 自动化（AppleScript + OCR），不 hook 微信进程。

## 依赖

- **localmac-ai-ocr** skill 必须已安装并配置好 `AISTUDIO_OCR_API_URL` 和 `AISTUDIO_OCR_TOKEN`
- macOS 系统工具：`osascript`, `screencapture`, `pbcopy`, `pbpaste`
- 微信（WeChat）已安装并登录

## 安装

此 skill 已安装到 `~/.openclaw/skills/wechat-auto/`

## 使用方法

### 命令行直接发送

```bash
# 发送消息给联系人
~/.openclaw/skills/wechat-auto/scripts/send_message "张三" "你好，这是自动消息"

# 调试模式，可以看到详细步骤
~/.openclaw/skills/wechat-auto/scripts/wechat_auto.py send "张三" "测试消息" --debug --delay 1.0
```

### 在 OpenClaw 中调用

你可以在 OpenClaw 会话中通过 `exec` 工具调用：

```json
{
  "tool": "exec",
  "parameters": {
    "command": "~/.openclaw/skills/wechat-auto/scripts/send_message \"张三\" \"你的消息\""
  }
}
```

或者用 Python 脚本集成：

```python
import subprocess
subprocess.run([
    "/Users/weiwang/.openclaw/skills/wechat-auto/scripts/send_message",
    "张三",
    "消息内容"
])
```

## 工作原理

1. **激活微信窗口**：通过 AppleScript 将 WeChat 置顶
2. **搜索联系人**：
   - 模拟打开搜索框（或通过 OCR 点击搜索区域）
   - 使用剪贴板粘贴联系人姓名（避免输入法激活）
   - OCR 识别搜索结果并点击
3. **发送消息**：
   - 定位消息输入框（通过 OCR 或默认位置）
   - 剪贴板粘贴消息内容
   - 模拟回车发送

## 权限要求

首次运行时，需要在 **系统设置 > 隐私与安全性 > 辅助功能** 中授权终端（Terminal）或你使用的 shell 进行 UI 控制。

如果提示权限不足，请：
1. 打开 系统设置 > 隐私与安全性 > 辅助功能
2. 点击 + 号添加 Terminal 或 iTerm
3. 勾选权限开关
4. 重新运行脚本

## 故障排除

### 找不到联系人
- 确保联系人名称准确（支持模糊匹配）
- 增加 `--delay` 时间给搜索留出加载时间
- 使用 `--debug` 查看 OCR 识别结果

### 点击位置错误
- WeChat 窗口尺寸/位置不同可能导致
- 尝试调整脚本中的坐标或使用 OCR 重新定位

### OCR 识别率低
- 检查 localmac-ai-ocr 是否正常工作
- 尝试设置 `--ocr-backend aistudio-ocr` 强制使用云端 OCR
- 确保 WeChat 窗口清晰可见，没有被遮挡

### 剪贴板粘贴失败
- 确保 `pbcopy`/`pbpaste` 可用（macOS 内置）
- 检查终端是否有权限访问剪贴板

## 安全说明

- 消息内容会短暂出现在剪贴板中，完成后不清除（为尊重用户隐私，你可以自行添加剪贴板清理逻辑）
- 脚本只操作本地 WeChat，不会通过网络发送数据（除了 OCR API）
- 不存储任何聊天记录或凭据

## License

MIT
