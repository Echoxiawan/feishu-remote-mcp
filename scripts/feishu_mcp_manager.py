#!/usr/bin/env python3
"""飞书 Remote MCP Token 与多客户端 MCP 配置管理脚本。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import stat
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


STATE_DIR = Path(os.environ.get("FEISHU_MCP_STATE_DIR", Path.home() / ".feishu-remote-mcp")).expanduser()
TOKEN_FILE = STATE_DIR / "token.json"
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_CONFIG_FILE = SCRIPT_DIR / "feishu_config.json"
SCRIPT_CONFIG_EXAMPLE_FILE = SCRIPT_DIR / "feishu_config.example.json"

FEISHU_MCP_URL = "https://mcp.feishu.cn/mcp"
DEFAULT_REDIRECT_URI = "http://localhost:8080/callback"
DEFAULT_ALLOWED_TOOLS = (
    "search-doc,create-doc,fetch-doc,update-doc,list-docs,"
    "get-comments,add-comments,search-user,get-user,fetch-file"
)
DEFAULT_SCOPE = (
    "docx:document:readonly docx:document:create docx:document:write_only "
    "search:docs:read wiki:wiki:readonly wiki:node:read "
    "contact:user:search contact:user.base:readonly "
    "docs:document.comment:read docs:document.comment:create "
    "board:whiteboard:node:create board:whiteboard:node:read board:whiteboard:node:update"
)
CLIENTS = ("claude", "cursor", "kiro", "codex")
SKILL_NAME = "feishu-remote-mcp"


def log(message: str) -> None:
    print(message, file=sys.stderr)


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE_DIR, 0o700)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent == STATE_DIR:
        ensure_state_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
    tmp_path.replace(path)


def write_json_config(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    tmp_path.replace(path)


def resolve_credentials() -> dict[str, str]:
    script_config = read_json(SCRIPT_CONFIG_FILE)
    app_id = script_config.get("app_id")
    app_secret = script_config.get("app_secret")
    redirect_uri = script_config.get("redirect_uri") or DEFAULT_REDIRECT_URI

    if not app_id or not app_secret:
        raise RuntimeError(
            f"缺少飞书应用凭证。请先创建 {SCRIPT_CONFIG_FILE}，"
            f"或运行 save-credentials 写入脚本配置文件。可参考 {SCRIPT_CONFIG_EXAMPLE_FILE}。"
        )
    return {"app_id": str(app_id), "app_secret": str(app_secret), "redirect_uri": str(redirect_uri)}


def request_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"网络请求失败: {exc.reason}") from exc


def get_app_access_token(credentials: dict[str, str]) -> str:
    result = request_json(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        {"app_id": credentials["app_id"], "app_secret": credentials["app_secret"]},
    )
    token = result.get("app_access_token")
    if not token:
        raise RuntimeError(f"获取 app_access_token 失败: {result.get('msg') or result.get('message') or result}")
    return str(token)


class CallbackServer:
    def __init__(self, redirect_uri: str) -> None:
        parsed = urllib.parse.urlparse(redirect_uri)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 8080
        self.path = parsed.path or "/callback"
        self.code: str | None = None
        self.error: str | None = None
        self._event = threading.Event()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed_url = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed_url.query)
                if parsed_url.path != outer.path:
                    self.send_response(404)
                    self.end_headers()
                    return
                if "code" in params:
                    outer.code = params["code"][0]
                    self._write_html("授权成功，可以关闭此窗口。")
                else:
                    outer.error = params.get("error", ["未收到授权码"])[0]
                    self._write_html("授权失败，请回到终端查看错误。")
                outer._event.set()

            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def _write_html(self, text: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = f"<!doctype html><meta charset='utf-8'><h1>{text}</h1>"
                self.wfile.write(html.encode("utf-8"))

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "CallbackServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def wait_for_code(self, timeout: int) -> str:
        if not self._event.wait(timeout):
            raise RuntimeError(f"等待授权超时，{timeout} 秒内没有收到飞书回调。")
        if self.error:
            raise RuntimeError(f"飞书授权失败: {self.error}")
        if not self.code:
            raise RuntimeError("飞书回调未包含授权码。")
        return self.code


def build_authorize_url(credentials: dict[str, str]) -> str:
    query = urllib.parse.urlencode(
        {
            "app_id": credentials["app_id"],
            "redirect_uri": credentials["redirect_uri"],
            "scope": DEFAULT_SCOPE,
        },
        quote_via=urllib.parse.quote,
    )
    return f"https://open.feishu.cn/open-apis/authen/v1/authorize?{query}"


def authorize_new_token(credentials: dict[str, str], timeout: int) -> dict[str, Any]:
    app_access_token = get_app_access_token(credentials)
    auth_url = build_authorize_url(credentials)
    log("正在打开浏览器进行飞书授权。")
    log(auth_url)
    with CallbackServer(credentials["redirect_uri"]) as callback:
        webbrowser.open(auth_url)
        code = callback.wait_for_code(timeout)

    result = request_json(
        "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
        {"grant_type": "authorization_code", "code": code},
        {"Authorization": f"Bearer {app_access_token}"},
    )
    data = result.get("data") or {}
    if not data.get("access_token") or not data.get("refresh_token"):
        raise RuntimeError(f"获取 User Access Token 失败: {result.get('message') or result}")
    return normalize_token_data(data)


def refresh_token(refresh_token_value: str) -> dict[str, Any]:
    result = request_json(
        "https://open.feishu.cn/open-apis/authen/v1/oidc/refresh_access_token",
        {"grant_type": "refresh_token", "refresh_token": refresh_token_value},
    )
    data = result.get("data") or {}
    if not data.get("access_token") or not data.get("refresh_token"):
        raise RuntimeError(f"刷新 User Access Token 失败: {result.get('message') or result}")
    return normalize_token_data(data)


def normalize_token_data(data: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    expires_in = int(data.get("expires_in") or 7200)
    refresh_expires_in = int(data.get("refresh_expires_in") or 2592000)
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": now + expires_in,
        "refresh_expires_at": now + refresh_expires_in,
        "updated_at": now,
    }


def get_fresh_token(force_reauth: bool, timeout: int, allow_interactive: bool) -> dict[str, Any]:
    existing = read_json(TOKEN_FILE)
    if not force_reauth and existing.get("refresh_token"):
        try:
            log("正在刷新飞书 User Access Token。")
            token_data = refresh_token(str(existing["refresh_token"]))
            write_json_private(TOKEN_FILE, token_data)
            return token_data
        except Exception as exc:
            log(f"refresh_token 刷新失败: {exc}")

    if not allow_interactive:
        raise RuntimeError("无法静默刷新 token，请先运行 prepare 完成浏览器授权。")

    credentials = resolve_credentials()
    token_data = authorize_new_token(credentials, timeout)
    write_json_private(TOKEN_FILE, token_data)
    return token_data


def feishu_headers(access_token: str, allowed_tools: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Lark-MCP-UAT": access_token,
        "X-Lark-MCP-Allowed-Tools": allowed_tools,
    }


def feishu_json_server(access_token: str, allowed_tools: str) -> dict[str, Any]:
    return {
        "url": FEISHU_MCP_URL,
        "headers": feishu_headers(access_token, allowed_tools),
        "disabled": False,
    }


def upsert_json_mcp(path: Path, server: dict[str, Any]) -> None:
    config = read_json(path)
    if not isinstance(config.get("mcpServers"), dict):
        config["mcpServers"] = {}
    config["mcpServers"]["feishu"] = server
    write_json_config(path, config)


def upsert_claude_config(project_root: Path, scope: str, access_token: str, allowed_tools: str) -> Path:
    if scope == "user":
        path = Path.home() / ".claude.json"
        server = {"type": "http", "url": FEISHU_MCP_URL, "headers": feishu_headers(access_token, allowed_tools)}
    else:
        path = project_root / ".mcp.json"
        helper = f"python3 {shlex.quote(str(Path(__file__).resolve()))} headers"
        server = {"type": "http", "url": FEISHU_MCP_URL, "headersHelper": helper}
    upsert_json_mcp(path, server)
    return path


def upsert_cursor_config(project_root: Path, scope: str, access_token: str, allowed_tools: str) -> Path:
    path = Path.home() / ".cursor" / "mcp.json" if scope == "user" else project_root / ".cursor" / "mcp.json"
    upsert_json_mcp(path, feishu_json_server(access_token, allowed_tools))
    return path


def upsert_kiro_config(project_root: Path, scope: str, access_token: str, allowed_tools: str) -> Path:
    path = Path.home() / ".kiro" / "settings" / "mcp.json" if scope == "user" else project_root / ".kiro" / "settings" / "mcp.json"
    upsert_json_mcp(path, feishu_json_server(access_token, allowed_tools))
    return path


def toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_codex_block(access_token: str, allowed_tools: str) -> str:
    return (
        "\n[mcp_servers.feishu]\n"
        f"url = {toml_quote(FEISHU_MCP_URL)}\n"
        "enabled = true\n"
        "\n[mcp_servers.feishu.headers]\n"
        f'"Content-Type" = {toml_quote("application/json")}\n'
        f'"X-Lark-MCP-UAT" = {toml_quote(access_token)}\n'
        f'"X-Lark-MCP-Allowed-Tools" = {toml_quote(allowed_tools)}\n'
    )


def upsert_codex_config(access_token: str, allowed_tools: str) -> Path:
    path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser() / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    block = build_codex_block(access_token, allowed_tools)
    pattern = re.compile(r"\n?\[mcp_servers\.feishu\][\s\S]*?(?=\n\[[^\]]+\]|\Z)", re.MULTILINE)
    if pattern.search(content):
        next_content = pattern.sub(block.rstrip("\n"), content, count=1)
    else:
        separator = "" if content.endswith("\n") or not content else "\n"
        next_content = content + separator + block.lstrip("\n")
    if next_content != content:
        path.write_text(next_content, encoding="utf-8")
    return path


def parse_clients(value: str) -> list[str]:
    if value == "all":
        return list(CLIENTS)
    clients = [item.strip().lower() for item in value.split(",") if item.strip()]
    invalid = sorted(set(clients) - set(CLIENTS))
    if invalid:
        raise RuntimeError(f"不支持的客户端: {', '.join(invalid)}")
    return clients


def default_skill_target_dir() -> Path:
    explicit = os.environ.get("FEISHU_MCP_SKILL_TARGET_DIR")
    if explicit:
        return Path(explicit).expanduser()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return codex_home / "skills"


def copy_skill_to_target(target_dir: Path) -> Path:
    source_dir = Path(__file__).resolve().parents[1]
    target_dir = target_dir.expanduser().resolve()
    target_skill_dir = target_dir / SKILL_NAME

    if source_dir == target_skill_dir:
        return target_skill_dir

    if target_skill_dir.exists():
        skill_file = target_skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise RuntimeError(f"目标目录已存在但不像 skill，拒绝覆盖: {target_skill_dir}")
        shutil.rmtree(target_skill_dir)

    def ignore(_: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {"__pycache__", ".DS_Store"} or name.endswith(".pyc")}

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_skill_dir, ignore=ignore)
    return target_skill_dir


def install(args: argparse.Namespace) -> None:
    installed_to = copy_skill_to_target(Path(args.target_dir))

    if args.app_id or args.app_secret:
        if not args.app_id or not args.app_secret:
            raise RuntimeError("安装时传入凭证必须同时提供 --app-id 和 --app-secret。")
        credential_data = {
            "app_id": args.app_id,
            "app_secret": args.app_secret,
            "redirect_uri": args.redirect_uri or DEFAULT_REDIRECT_URI,
        }
        write_json_private(SCRIPT_CONFIG_FILE, credential_data)
        log(f"飞书应用凭证已保存到 {SCRIPT_CONFIG_FILE}")
        installed_config_file = installed_to / "scripts" / "feishu_config.json"
        if installed_config_file != SCRIPT_CONFIG_FILE:
            write_json_private(installed_config_file, credential_data)
            log(f"飞书应用凭证已保存到 {installed_config_file}")

    updated: dict[str, str] = {}
    if args.prepare_mcp:
        clients = parse_clients(args.clients)
        project_root = Path(args.project_root).resolve()
        allowed_tools = args.allowed_tools or os.environ.get("FEISHU_MCP_ALLOWED_TOOLS") or DEFAULT_ALLOWED_TOOLS
        token_data = get_fresh_token(args.force_reauth, args.timeout, allow_interactive=True)
        access_token = str(token_data["access_token"])
        for client in clients:
            if client == "claude":
                updated[client] = str(upsert_claude_config(project_root, args.scope, access_token, allowed_tools))
            elif client == "cursor":
                updated[client] = str(upsert_cursor_config(project_root, args.scope, access_token, allowed_tools))
            elif client == "kiro":
                updated[client] = str(upsert_kiro_config(project_root, args.scope, access_token, allowed_tools))
            elif client == "codex":
                updated[client] = str(upsert_codex_config(access_token, allowed_tools))

    print(
        json.dumps(
            {
                "installed_to": str(installed_to),
                "script_config_file": str(installed_to / "scripts" / "feishu_config.json"),
                "token_file": str(TOKEN_FILE),
                "updated": updated,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def save_credentials(args: argparse.Namespace) -> None:
    data = {
        "app_id": args.app_id,
        "app_secret": args.app_secret,
        "redirect_uri": args.redirect_uri or DEFAULT_REDIRECT_URI,
    }
    write_json_private(SCRIPT_CONFIG_FILE, data)
    log(f"飞书应用凭证已保存到 {SCRIPT_CONFIG_FILE}")


def prepare(args: argparse.Namespace) -> None:
    clients = parse_clients(args.clients)
    project_root = Path(args.project_root).resolve()
    allowed_tools = args.allowed_tools or os.environ.get("FEISHU_MCP_ALLOWED_TOOLS") or DEFAULT_ALLOWED_TOOLS
    token_data = get_fresh_token(args.force_reauth, args.timeout, allow_interactive=True)
    access_token = str(token_data["access_token"])

    updated: dict[str, str] = {}
    for client in clients:
        if client == "claude":
            updated[client] = str(upsert_claude_config(project_root, args.scope, access_token, allowed_tools))
        elif client == "cursor":
            updated[client] = str(upsert_cursor_config(project_root, args.scope, access_token, allowed_tools))
        elif client == "kiro":
            updated[client] = str(upsert_kiro_config(project_root, args.scope, access_token, allowed_tools))
        elif client == "codex":
            updated[client] = str(upsert_codex_config(access_token, allowed_tools))

    print(json.dumps({"updated": updated, "token_file": str(TOKEN_FILE)}, ensure_ascii=False, indent=2))


def headers(args: argparse.Namespace) -> None:
    allowed_tools = args.allowed_tools or os.environ.get("FEISHU_MCP_ALLOWED_TOOLS") or DEFAULT_ALLOWED_TOOLS
    token_data = get_fresh_token(False, 0, allow_interactive=False)
    print(json.dumps(feishu_headers(str(token_data["access_token"]), allowed_tools), ensure_ascii=False))


def status(_: argparse.Namespace) -> None:
    token_data = read_json(TOKEN_FILE)
    output = {
        "script_config_file": str(SCRIPT_CONFIG_FILE),
        "token_file": str(TOKEN_FILE),
        "has_credentials": SCRIPT_CONFIG_FILE.exists(),
        "has_refresh_token": bool(token_data.get("refresh_token")),
        "expires_at": token_data.get("expires_at"),
        "refresh_expires_at": token_data.get("refresh_expires_at"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理飞书 Remote MCP Token 与多客户端 MCP 配置。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="安装 skill，可同时保存凭证并生成 MCP 配置。")
    install_parser.add_argument("--target-dir", default=str(default_skill_target_dir()), help="目标 skills 根目录。")
    install_parser.add_argument("--app-id", default=None, help="飞书自建应用 App ID。")
    install_parser.add_argument("--app-secret", default=None, help="飞书自建应用 App Secret。")
    install_parser.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI, help="飞书应用安全设置中的重定向 URL。")
    install_parser.add_argument("--prepare-mcp", action="store_true", help="安装后立即刷新 token 并写入 MCP 配置。")
    install_parser.add_argument("--clients", default="all", help="all 或逗号分隔列表：claude,cursor,kiro,codex。")
    install_parser.add_argument("--scope", choices=("project", "user"), default="project", help="写入项目级或用户级 MCP 配置。")
    install_parser.add_argument("--project-root", default=".", help="项目根目录，默认当前目录。")
    install_parser.add_argument("--force-reauth", action="store_true", help="跳过刷新，强制重新浏览器授权。")
    install_parser.add_argument("--timeout", type=int, default=180, help="等待浏览器授权回调的秒数。")
    install_parser.add_argument("--allowed-tools", default=None, help="覆盖 X-Lark-MCP-Allowed-Tools。")
    install_parser.set_defaults(func=install)

    save = subparsers.add_parser("save-credentials", help="保存飞书应用凭证。")
    save.add_argument("--app-id", required=True, help="飞书自建应用 App ID。")
    save.add_argument("--app-secret", required=True, help="飞书自建应用 App Secret。")
    save.add_argument("--redirect-uri", default=DEFAULT_REDIRECT_URI, help="飞书应用安全设置中的重定向 URL。")
    save.set_defaults(func=save_credentials)

    prepare_parser = subparsers.add_parser("prepare", help="刷新或重新获取 token，并同步 MCP 配置。")
    prepare_parser.add_argument("--clients", default="all", help="all 或逗号分隔列表：claude,cursor,kiro,codex。")
    prepare_parser.add_argument("--scope", choices=("project", "user"), default="project", help="写入项目级或用户级配置。")
    prepare_parser.add_argument("--project-root", default=".", help="项目根目录，默认当前目录。")
    prepare_parser.add_argument("--force-reauth", action="store_true", help="跳过刷新，强制重新浏览器授权。")
    prepare_parser.add_argument("--timeout", type=int, default=180, help="等待浏览器授权回调的秒数。")
    prepare_parser.add_argument("--allowed-tools", default=None, help="覆盖 X-Lark-MCP-Allowed-Tools。")
    prepare_parser.set_defaults(func=prepare)

    headers_parser = subparsers.add_parser("headers", help="输出 Claude Code headersHelper 需要的 JSON headers。")
    headers_parser.add_argument("--allowed-tools", default=None, help="覆盖 X-Lark-MCP-Allowed-Tools。")
    headers_parser.set_defaults(func=headers)

    status_parser = subparsers.add_parser("status", help="查看本地 token 与凭证状态。")
    status_parser.set_defaults(func=status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        log(f"错误: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
