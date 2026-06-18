# feishu-remote-mcp

为 Claude Code、Cursor、Kiro、Codex 配置飞书 Remote MCP，支持 User Access Token 自动刷新、浏览器重授权、多客户端 MCP 配置幂等写入。

> 仓库地址：https://github.com/Echoxiawan/feishu-remote-mcp

---

## 功能

- 自动刷新飞书 User Access Token（有效期 2 小时）
- Refresh Token 失效时自动打开浏览器重新授权（有效期 30 天）
- 支持 Claude Code（`headersHelper` 动态 Header）、Cursor、Kiro、Codex
- 项目级 / 用户级 MCP 配置自由切换
- 凭证文件权限 `0600`，不提交到仓库

---

## 前置条件

1. Python 3.8+
2. 飞书自建应用，获取 `APP_ID` 和 `APP_SECRET`
3. 在飞书应用安全设置中添加重定向 URL：

   ```
   http://localhost:8080/callback
   ```

4. 为应用开通以下权限（建议）：

   ```
   docx:document:readonly
   docx:document:create
   docx:document:write_only
   search:docs:read
   wiki:wiki:readonly
   wiki:node:read
   contact:user:search
   contact:user.base:readonly
   docs:document.comment:read
   docs:document.comment:create
   board:whiteboard:node:create
   board:whiteboard:node:read
   board:whiteboard:node:update
   ```

---

## 安装

### 方式一：让 AI 自动安装（推荐）

将以下提示词发送给支持工具调用的 AI（Claude Code、Cursor、Kiro、Codex 等）：

```
请帮我安装飞书 Remote MCP。

首先询问我以下信息，获取后再继续：
1. 飞书应用的 APP_ID
2. 飞书应用的 APP_SECRET

获取到凭证后，按以下步骤完成安装：
1. 克隆仓库到当前目录：
   git clone https://github.com/Echoxiawan/feishu-remote-mcp.git
2. 读取 feishu-remote-mcp/INSTALL.md，按文档完成安装
3. 为所有支持的客户端（Claude Code、Cursor、Kiro、Codex）配置 MCP，使用项目级配置
```

AI 会先向你索取 APP_ID 和 APP_SECRET，拿到后自动完成克隆、凭证写入、浏览器授权、MCP 配置写入全流程。

---

### 方式二：手动安装

**1. 克隆仓库**

```bash
git clone https://github.com/Echoxiawan/feishu-remote-mcp.git
```

**2. 保存飞书应用凭证**

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "你的APP_ID" \
  --app-secret "你的APP_SECRET"
```

**3. 完成授权并写入 MCP 配置（所有客户端，项目级）**

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py install \
  --app-id "你的APP_ID" \
  --app-secret "你的APP_SECRET" \
  --prepare-mcp \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

执行后会自动打开浏览器完成飞书授权，获取 token 并写入各客户端 MCP 配置。

---

## MCP 配置写入位置

| 客户端 | 项目级 | 用户级 |
|--------|--------|--------|
| Claude Code | `.mcp.json` | `~/.claude.json` |
| Cursor | `.cursor/mcp.json` | `~/.cursor/mcp.json` |
| Kiro | `.kiro/settings/mcp.json` | `~/.kiro/settings/mcp.json` |
| Codex | — | `~/.codex/config.toml` |

切换项目级 / 用户级：

```bash
--scope project   # 项目级（默认）
--scope user      # 用户级
```

---

## 日常使用

### 刷新 Token

每次调用飞书 MCP 前，刷新 token 并同步配置：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

**Claude Code** 使用 `headersHelper`，连接时自动调用脚本刷新，无需手动执行。

### 查看状态

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py status
```

### 强制重新授权

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --force-reauth \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

---

## 可用 MCP 工具

| 工具 | 说明 |
|------|------|
| `search-doc` | 搜索云文档 |
| `create-doc` | 创建云文档 |
| `fetch-doc` | 查看云文档内容 |
| `update-doc` | 更新云文档 |
| `list-docs` | 获取文档列表 |
| `get-comments` | 查看评论 |
| `add-comments` | 添加评论 |
| `search-user` | 搜索用户 |
| `get-user` | 获取用户信息 |
| `fetch-file` | 获取文件或图片内容 |

---

## 安全说明

- `feishu_config.json`（存储 APP_ID / APP_SECRET）已被 `.gitignore` 忽略，不会提交到仓库
- Token 存放在 `~/.feishu-remote-mcp/token.json`，权限为 `0600`
- 不要将 APP_SECRET、access_token、refresh_token 提交到任何仓库
