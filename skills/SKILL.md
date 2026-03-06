---
name: wechat-auto
description: Use when you need to automate sending messages via WeChat on macOS. Uses GUI automation with OCR assistance to activate WeChat window, search for contacts, and send messages without triggering input method. No hooking or private APIs - pure UI automation.
metadata:
    openclaw:
        requires:
            bins:
                - python3
                - osascript
                - sips
                - pbpaste
                - pbcopy
            skills:
                - localmac-ai-ocr
        primaryEnv: OCR_SKILL_PYTHON
---

# WeChat Auto (macOS GUI Automation)

**Note**: This skill depends on `localmac-ai-ocr` for OCR capabilities. Ensure it is installed and configured first.

## Overview

This skill automates WeChat messaging on macOS by:

1. Activating the WeChat application window
2. Using OCR to locate UI elements (search box, contact names, input field)
3. Copying message text to clipboard and pasting (avoiding input method activation)
4. Simulating mouse clicks and keyboard shortcuts

It does **NOT** use any private APIs or hook into WeChat processes - it's pure UI automation.

## Installation

The skill is automatically installed with its dependencies. Just ensure `localmac-ai-ocr` is properly configured with `AISTUDIO_OCR_API_URL` and `AISTUDIO_OCR_TOKEN`.

## Usage

### Command Line

```bash
# Send a message to a contact
wechat-auto send "Contact Name" "Your message here"

# With options
wechat-auto send "Contact Name" "Your message" --delay 0.5 --ocr-backend aistudio-ocr
```

### Python API

```python
from wechat_auto import WeChatAuto

wc = WeChatAuto()
wc.send_message("Contact Name", "Hello from OpenClaw!")
```

## How It Works

1. **Activate WeChat**: Uses AppleScript to bring WeChat to foreground
2. **Open Search**: Simulates Cmd+F (or clicks search box if needed)
3. **Search Contact**: Types contact name (via clipboard paste to avoid IME)
4. **Select Contact**: Clicks on the first match using coordinates from OCR
5. **Type Message**: Pastes message from clipboard into input field
6. **Send**: Simulates Return key or clicks send button

## Requirements

- macOS with WeChat installed
- `localmac-ai-ocr` skill installed and configured
- Permissions: Accessibility access for the terminal/Python (System Settings > Privacy & Security > Accessibility)
- WeChat must be logged in and visible in the dock

## Limitations

- Window positions/coordinates may vary; OCR helps but can be slow
- WeChat UI changes may break automation
- Only works on local machine (not headless servers)
- Requires WeChat to be installed and licensed

## Troubleshooting

If automation fails:

1. Check OCR is working: `ocr ocr screenshot.png`
2. Ensure WeChat window is not minimized
3. Grant Accessibility permissions to your shell/terminal
4. Increase `--delay` if clicks are missed
5. Use `--debug` to see OCR output and coordinates
