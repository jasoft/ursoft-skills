# ursoft-skills

本仓库用于维护一组可复用的本地 agent skills。每个 skill 独立放在 `skills/` 目录下，按用途组织文档、脚本、参考资料与测试。

## 当前结构

```text
.
├── AGENTS.md
├── README.md
├── .gitignore
└── skills/
    ├── localmac-ai-ocr/
    ├── mumu-manager-cli/
    └── wechat-send/
```

## 目录约定

- `skills/<name>/SKILL.md`：skill 主说明，定义用途、触发场景、前置依赖、执行流程
- `skills/<name>/references/`：补充资料与命令手册
- `skills/<name>/scripts/`：脚本、依赖声明、安装辅助文件
- `skills/<name>/tests/`：和脚本或关键能力对应的测试
- `skills/<name>/agents/`：额外 agent 配置

## 维护原则

- 每个 skill 应该自描述，优先通过 `SKILL.md` 让协作者快速上手
- 文档中的命令示例应与脚本真实参数保持一致
- 本地环境文件、密钥、缓存目录不进入版本控制
- 对 skill 的改动尽量聚焦，避免无关文件一起修改

## 新增 Skill 最低要求

新增一个 skill 时，建议至少包含以下内容：

1. `SKILL.md`
2. 必要的 `references/` 或 `scripts/`
3. 若存在可执行逻辑，给出最小验证方式

## 已有 Skills

- `localmac-ai-ocr`：面向 macOS / RDP 场景的截图、OCR、按文字定位与点击
- `mumu-manager-cli`：面向 MuMu 模拟器 12 的命令行管理与自动化操作
- `wechat-send`：在 macOS 桌面版微信上自动化发送消息，支持剪贴板粘贴与 OCR 校验

## 建议工作流

1. 在对应 skill 目录下更新 `SKILL.md`、脚本或参考资料
2. 运行该 skill 的最小验证命令或测试
3. 检查是否误提交 `.env`、`.venv`、缓存或截图产物
4. 再进行提交
