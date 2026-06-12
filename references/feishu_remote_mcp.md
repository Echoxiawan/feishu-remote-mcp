# 飞书 Remote MCP 参考

来源：

- Book of Kiro 飞书 Remote MCP 配置：https://kiro-community.github.io/book-of-kiro/kiro-experience/feishu-remote-mcp/
- Claude Code MCP 文档：https://code.claude.com/docs/en/mcp
- Kiro IDE MCP 配置：https://kiro.dev/docs/mcp/configuration/
- Kiro CLI MCP 配置：https://kiro.dev/docs/cli/mcp/configuration/
- Cursor MCP 文档：https://cursor.com/docs/mcp

## 飞书 Remote MCP

- 服务地址：`https://mcp.feishu.cn/mcp`
- 认证方式：HTTP Header
- 必需 Header：
  - `Content-Type: application/json`
  - `X-Lark-MCP-UAT: <user_access_token>`
  - `X-Lark-MCP-Allowed-Tools: search-doc,create-doc,fetch-doc,update-doc,list-docs,get-comments,add-comments,search-user,get-user,fetch-file`

## Token

- User Access Token 通常以 `u-` 开头，有效期约 2 小时。
- Refresh Token 有效期约 30 天。
- 每次准备调用 MCP 前都运行 `scripts/feishu_mcp_manager.py prepare`，主动 refresh 并写回配置。
- refresh 失败时，脚本自动启动本地回调服务并打开浏览器重新授权。

## 飞书应用前置要求

飞书自建应用需要在安全设置中配置重定向 URL，默认：

```text
http://localhost:8080/callback
```

建议权限：

```text
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

## 可用工具

- `search-doc`：搜索云文档
- `create-doc`：创建云文档
- `fetch-doc`：查看云文档
- `update-doc`：更新云文档
- `list-docs`：获取文档列表
- `get-comments`：查看评论
- `add-comments`：添加评论
- `search-user`：搜索用户
- `get-user`：获取用户信息
- `fetch-file`：获取文件或图片内容
