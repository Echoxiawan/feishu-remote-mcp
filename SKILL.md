---
name: feishu-remote-mcp
description: Configure and use Feishu/Lark Remote MCP across Claude Code, Cursor, Kiro, and Codex with automatic User Access Token refresh, browser reauthorization when refresh tokens expire, and idempotent MCP config updates. Use when an agent needs Feishu cloud document MCP tools, needs to refresh or reissue X-Lark-MCP-UAT, or needs to generate/update MCP config for Feishu Remote MCP.
---

# 飞书 Remote MCP

## 核心规则

使用飞书 MCP 前，先运行本 skill 的脚本刷新 token 并同步 MCP 配置。脚本会优先 refresh；refresh 失效时自动打开浏览器重新授权；配置已存在时只更新对应 `feishu` 条目，不重复添加。

安装或迁移本 skill 时，先读取 `INSTALL.md`。

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare --clients all --scope project
```

## 首次凭证

如果用户已经提供飞书应用凭证，则先保存到脚本目录配置文件：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py save-credentials \
  --app-id "替换为飞书APP_ID" \
  --app-secret "替换为飞书APP_SECRET" \
  --redirect-uri "http://localhost:8080/callback"
```

凭证配置文件为 `scripts/feishu_config.json`，文件权限为 `0600`，已被 `.gitignore` 忽略。token 默认存放在 `~/.feishu-remote-mcp/token.json`。

## 客户端适配

默认 `--clients all` 会处理：

- Claude Code：项目级 `.mcp.json`，使用 `headersHelper` 动态生成 headers；先运行 `prepare` 完成授权，之后 Claude Code 连接时可自动 refresh。
- Cursor：项目级 `.cursor/mcp.json`，写入静态 headers；每次需要飞书 MCP 前再次运行 `prepare` 刷新并回填。
- Kiro：项目级 `.kiro/settings/mcp.json`，写入静态 headers；每次需要飞书 MCP 前再次运行 `prepare` 刷新并回填。
- Codex：用户级 `~/.codex/config.toml`，写入静态 headers；每次需要飞书 MCP 前再次运行 `prepare` 刷新并回填。

如只配置某些客户端：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare --clients claude,cursor,kiro
```

## 运行状态

查看本地状态：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py status
```

强制重新浏览器授权：

```bash
python3 feishu-remote-mcp/scripts/feishu_mcp_manager.py prepare --force-reauth
```

## 参考资料

需要确认飞书 Remote MCP 地址、Header、权限、工具白名单，读取 `references/feishu_remote_mcp.md`。
