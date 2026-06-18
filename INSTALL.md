# 飞书 Remote MCP Skill 安装指南

本文档给 AI Agent 使用。支持两种安装方式，按场景选择。

**仓库地址**：`https://github.com/Echoxiawan/feishu-remote-mcp`

---

## 方式一：从远程仓库直接安装（推荐）

无需先 clone 到本地，直接 clone 到各 Agent 的 skill 目录，再从安装位置运行配置脚本。

### 前置条件

需要用户提供飞书自建应用凭证：`APP_ID`、`APP_SECRET`。  
飞书应用安全设置中需添加重定向 URL（默认 `http://localhost:8080/callback`）。

### 各 Agent 安装命令

**Claude Code**
```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git ~/.claude/skills/feishu-remote-mcp
python3 ~/.claude/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "APP_ID" --app-secret "APP_SECRET"
python3 ~/.claude/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients claude --scope project --project-root "$(pwd)"
```

**Kiro**
```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git ~/.kiro/skills/feishu-remote-mcp
python3 ~/.kiro/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "APP_ID" --app-secret "APP_SECRET"
python3 ~/.kiro/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients kiro --scope project --project-root "$(pwd)"
```

**Cursor**
```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git ~/.cursor/skills/feishu-remote-mcp
python3 ~/.cursor/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "APP_ID" --app-secret "APP_SECRET"
python3 ~/.cursor/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients cursor --scope project --project-root "$(pwd)"
```

**Codex**
```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git ~/.codex/skills/feishu-remote-mcp
python3 ~/.codex/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "APP_ID" --app-secret "APP_SECRET"
python3 ~/.codex/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients codex --scope project --project-root "$(pwd)"
```

**所有客户端同时配置**（clone 一次，MCP 配置写入全部客户端）
```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git ~/.claude/skills/feishu-remote-mcp
python3 ~/.claude/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "APP_ID" --app-secret "APP_SECRET"
python3 ~/.claude/skills/feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients all --scope project --project-root "$(pwd)"
```

---

## 方式二：从本地已有仓库安装

适用于已将本仓库 clone 到本地的情况。所有路径相对于本文件所在目录。

### 各 Agent 安装命令

**Claude Code**
```bash
python3 scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.claude/skills" \
  --app-id "APP_ID" --app-secret "APP_SECRET" \
  --prepare-mcp --clients claude --scope project --project-root "$(pwd)"
```

**Kiro**
```bash
python3 scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.kiro/skills" \
  --app-id "APP_ID" --app-secret "APP_SECRET" \
  --prepare-mcp --clients kiro --scope project --project-root "$(pwd)"
```

**Cursor**
```bash
python3 scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.cursor/skills" \
  --app-id "APP_ID" --app-secret "APP_SECRET" \
  --prepare-mcp --clients cursor --scope project --project-root "$(pwd)"
```

**Codex**
```bash
python3 scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.codex/skills" \
  --app-id "APP_ID" --app-secret "APP_SECRET" \
  --prepare-mcp --clients codex --scope project --project-root "$(pwd)"
```

---

## 安装验证

```bash
python3 <skill安装路径>/scripts/feishu_mcp_manager.py status
```

## 安全准则

- `APP_SECRET`、token 不写入仓库
- 凭证统一存 `scripts/feishu_config.json`（权限 0600，已 gitignore）
- token 通过脚本管理，不手动编辑
