---
name: feishu-remote-mcp
description: 配置并使用飞书/Feishu/Lark Remote MCP，支持飞书云文档、多维表格、知识库、Wiki 等工具访问。触发条件：用户提到飞书文档/飞书 MCP/飞书工具，或需要读写飞书云文档、多维表格、知识库，或需要刷新 X-Lark-MCP-UAT token，或需要为 Claude Code/Cursor/Kiro/Codex 生成飞书 MCP 配置。自动处理 token refresh 和浏览器重新授权，幂等更新 MCP 配置。
---

# 飞书 Remote MCP

> 所有路径均相对于本 SKILL.md 所在目录。查看完整命令选项：`python3 scripts/feishu_mcp_manager.py --help`

## 决策树

```
需要使用飞书 MCP？
├── 首次使用 / 没有凭证 → 读取 INSTALL.md，按流程安装
├── 有凭证，需要刷新 token 或更新 MCP 配置 → 执行"每次使用前"命令
└── token 过期 / 浏览器重新授权 → 执行"强制重新授权"命令
```

## 每次使用前

```bash
python3 scripts/feishu_mcp_manager.py prepare --clients all --scope project
```

## 常用命令

```bash
# 查看当前状态（token 是否有效、凭证路径等）
python3 scripts/feishu_mcp_manager.py status

# 只配置指定客户端
python3 scripts/feishu_mcp_manager.py prepare --clients claude,cursor,kiro --scope project

# 强制浏览器重新授权
python3 scripts/feishu_mcp_manager.py prepare --force-reauth --clients all --scope project
```

## 配置写入位置

项目级（`--scope project`）：

- Claude Code：`<project-root>/.mcp.json`（使用 `headersHelper` 动态 refresh，无需每次手动 prepare）
- Cursor：`<project-root>/.cursor/mcp.json`
- Kiro：`<project-root>/.kiro/settings/mcp.json`
- Codex：`~/.codex/config.toml`

用户级（`--scope user`）：`~/.claude.json` / `~/.cursor/mcp.json` / `~/.kiro/settings/mcp.json`

## 安全准则

- 凭证（`APP_SECRET`、token）不提交到仓库，统一存 `scripts/feishu_config.json`（已 gitignore）
- token 通过脚本刷新，不手动编辑

## 参考资料

需要确认飞书 Remote MCP 地址、Header、权限、工具白名单：读取 `references/feishu_remote_mcp.md`
