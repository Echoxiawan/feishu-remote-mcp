# 飞书 Remote MCP Skill 安装与配置

本文档给 AI Agent 使用。读取到本文件后，按下面流程安装 `feishu-remote-mcp` skill，并在安装时保存飞书应用凭证、生成 MCP 配置。

## 适用目标

该 skill 用于配置飞书 Remote MCP，支持以下客户端：

- Claude Code
- Cursor
- Kiro
- Codex

飞书 Remote MCP 地址固定为：

```text
https://mcp.feishu.cn/mcp
```

## 前置条件

需要用户提供飞书自建应用凭证：

- `APP_ID`
- `APP_SECRET`

飞书应用安全设置中需要配置重定向 URL，默认值：

```text
http://localhost:8080/callback
```

## 配置文件方式保存凭证

优先使用脚本目录下的配置文件保存飞书凭证。AI 安装时可以直接创建：

```bash
cp feishu-remote-mcp/scripts/feishu_config.example.json \
  feishu-remote-mcp/scripts/feishu_config.json
```

然后把 `feishu_config.json` 改成：

```json
{
  "app_id": "替换为飞书APP_ID",
  "app_secret": "替换为飞书APP_SECRET",
  "redirect_uri": "http://localhost:8080/callback"
}
```

`feishu_config.json` 已被 `.gitignore` 忽略，不要提交到仓库。

也可以让脚本代写配置文件：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "替换为飞书APP_ID" \
  --app-secret "替换为飞书APP_SECRET"
```

该命令会写入：

```text
feishu-remote-mcp/scripts/feishu_config.json
```

## 一步安装并保存凭证

在包含 `feishu-remote-mcp` 目录的项目根目录执行：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.codex/skills" \
  --app-id "替换为飞书APP_ID" \
  --app-secret "替换为飞书APP_SECRET"
```

说明：

- `--target-dir` 是目标 skills 根目录。
- 如果当前工具不是 Codex，但也支持本地 skill 目录，将 `--target-dir` 改成该工具的 skills 根目录。
- 如果目标工具不支持 skills，仍可保留本项目里的 `feishu-remote-mcp` 目录，直接调用脚本管理 token 和 MCP 配置。
- 凭证会保存到 `feishu-remote-mcp/scripts/feishu_config.json`，权限为 `0600`。

## 一步安装、保存凭证并生成 MCP 配置

如果用户允许浏览器授权，可以一次性完成安装、凭证保存、token 获取和 MCP 配置写入：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py install \
  --target-dir "$HOME/.codex/skills" \
  --app-id "替换为飞书APP_ID" \
  --app-secret "替换为飞书APP_SECRET" \
  --prepare-mcp \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

执行后脚本会：

- 保存飞书 `APP_ID` 和 `APP_SECRET` 到 `scripts/feishu_config.json`；
- 打开浏览器完成飞书授权；
- 获取 User Access Token 和 Refresh Token；
- 写入或更新 MCP 配置；
- 如果 MCP 配置里已有 `feishu`，只更新该条目，不重复添加。

## 只配置指定客户端

`--clients` 支持 `all` 或逗号分隔列表：

```bash
--clients claude,cursor,kiro,codex
```

示例：只配置 Claude Code、Cursor、Kiro：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients claude,cursor,kiro \
  --scope project \
  --project-root "$(pwd)"
```

## 配置文件写入位置

项目级配置：

- Claude Code：`<project-root>/.mcp.json`
- Cursor：`<project-root>/.cursor/mcp.json`
- Kiro：`<project-root>/.kiro/settings/mcp.json`
- Codex：`~/.codex/config.toml`

用户级配置：

- Claude Code：`~/.claude.json`
- Cursor：`~/.cursor/mcp.json`
- Kiro：`~/.kiro/settings/mcp.json`
- Codex：`~/.codex/config.toml`

切换项目级或用户级：

```bash
--scope project
--scope user
```

## 每次使用前刷新 token

每次需要调用飞书 MCP 前，先执行：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

行为：

- 有 refresh token 时，先主动 refresh；
- refresh token 失效时，自动打开浏览器重新授权；
- 自动把最新 `X-Lark-MCP-UAT` 写入对应 MCP 配置。

## Claude Code 动态 Header

项目级 Claude Code 配置使用 `headersHelper`。安装或 `prepare` 后会写入：

```json
{
  "mcpServers": {
    "feishu": {
      "type": "http",
      "url": "https://mcp.feishu.cn/mcp",
      "headersHelper": "python3 <skill路径>/scripts/feishu_mcp_manager.py headers"
    }
  }
}
```

Claude Code 每次连接 MCP 时会调用 `headersHelper`。该命令会刷新 token 并输出：

```json
{
  "Content-Type": "application/json",
  "X-Lark-MCP-UAT": "u-...",
  "X-Lark-MCP-Allowed-Tools": "search-doc,create-doc,fetch-doc,update-doc,list-docs,get-comments,add-comments,search-user,get-user,fetch-file"
}
```

## 状态检查

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py status
```

输出会显示：

- 凭证文件路径
- 脚本配置文件路径
- token 文件路径
- 是否已有凭证
- 是否已有 refresh token
- token 过期时间戳

## 强制重新授权

如果用户明确要求重新登录飞书，执行：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare \
  --force-reauth \
  --clients all \
  --scope project \
  --project-root "$(pwd)"
```

## AI 执行准则

- 不要把 `APP_SECRET`、`access_token`、`refresh_token` 写入项目仓库。
- `APP_ID` 和 `APP_SECRET` 写入 `feishu-remote-mcp/scripts/feishu_config.json`，不要使用环境变量。
- 不要手工编辑 token，统一通过脚本刷新和写入。
- 如果用户提供了 `APP_ID` 和 `APP_SECRET`，优先使用 `install --app-id ... --app-secret ...`。
- 如果用户只要求生成 MCP 配置，执行 `prepare`。
- 如果 refresh 失败，脚本会自动浏览器授权，不需要改代码。
