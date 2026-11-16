"""平台兼容层与跨平台 GUI 适配的回归检查。

用法：.venv\\Scripts\\python.exe tools\\check_platform_compat.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"   {'OK  ' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def case_compat() -> None:
    print("== platform_compat ==")
    from essay_tool import platform_compat as pc

    mac = pc._resolve("darwin", {})
    check("darwin UI_FONT == PingFang SC", mac["UI_FONT"] == "PingFang SC", repr(mac))
    check("darwin MOD_LABEL == ⌘", mac["MOD_LABEL"] == "⌘", repr(mac))
    check("darwin MOD_KEY == Command", mac["MOD_KEY"] == "Command", repr(mac))
    check("darwin IS_MAC/UI_MAC", mac["IS_MAC"] is True and mac["UI_MAC"] is True, repr(mac))

    win = pc._resolve("win32", {})
    check("win32 UI_FONT == Microsoft YaHei UI", win["UI_FONT"] == "Microsoft YaHei UI", repr(win))
    check("win32 MOD_LABEL == Ctrl", win["MOD_LABEL"] == "Ctrl", repr(win))
    check("win32 MOD_KEY == Control", win["MOD_KEY"] == "Control", repr(win))
    check("win32 IS_WIN/UI_MAC", win["IS_WIN"] is True and win["UI_MAC"] is False, repr(win))

    prev = pc._resolve("win32", {"ESSAY_TOOL_UI_PREVIEW": "mac"})
    check(
        "win32 预览模式保持 Windows 字体但 UI_MAC=True",
        prev["UI_MAC"] is True and prev["IS_MAC"] is False and prev["UI_FONT"] == "Microsoft YaHei UI",
        repr(prev),
    )

    mac_base = pc.user_data_base("darwin", {}, pathlib.Path("/Users/test"))
    check(
        "darwin user_data_base",
        mac_base == pathlib.Path("/Users/test/Library/Application Support"),
        repr(mac_base),
    )
    win_base = pc.user_data_base("win32", {"APPDATA": "/fake/roaming"}, pathlib.Path("/Users/test"))
    check("win32 user_data_base", win_base == pathlib.Path("/fake/roaming"), repr(win_base))

    orig_win, orig_mac = pc.IS_WIN, pc.IS_MAC
    orig_run = subprocess.run
    calls: list[tuple[object, dict]] = []
    try:
        pc.IS_WIN, pc.IS_MAC = False, True

        def fake_run(cmd, **kw):
            calls.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0)

        subprocess.run = fake_run
        pc.open_path("/tmp/中文 空格/备份")
        check(
            "open_path macOS 参数列表与无 shell=True",
            len(calls) == 1
            and calls[0][0] == ["open", "/tmp/中文 空格/备份"]
            and calls[0][1].get("shell") is not True
            and calls[0][1].get("check") is True,
            repr(calls),
        )

        def failing_run(cmd, **kw):
            raise subprocess.CalledProcessError(1, cmd)

        subprocess.run = failing_run
        got_os_err = False
        try:
            pc.open_path("/tmp/not_exists")
        except OSError:
            got_os_err = True
        check("open_path 子进程失败转为 OSError", got_os_err)
    finally:
        pc.IS_WIN, pc.IS_MAC = orig_win, orig_mac
        subprocess.run = orig_run

    orig_certifi = sys.modules.get("certifi", ...)
    orig_ssl_env = os.environ.pop("SSL_CERT_FILE", None)
    try:
        pc.IS_MAC = True
        sys.modules["certifi"] = None  # type: ignore[assignment]
        check("ensure_ssl_certs 缺 certifi 不抛异常", pc.ensure_ssl_certs() is False)

        if orig_certifi is ...:
            sys.modules.pop("certifi", None)
        else:
            sys.modules["certifi"] = orig_certifi
        os.environ.pop("SSL_CERT_FILE", None)
        ok_cert = pc.ensure_ssl_certs()
        env_cert = os.environ.get("SSL_CERT_FILE", "")
        check("ensure_ssl_certs 有 certifi 时设置 SSL_CERT_FILE", ok_cert is True and os.path.isfile(env_cert), env_cert)
    finally:
        pc.IS_MAC = orig_mac
        if orig_certifi is ...:
            sys.modules.pop("certifi", None)
        else:
            sys.modules["certifi"] = orig_certifi
        if orig_ssl_env is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = orig_ssl_env


def main() -> int:
    case_compat()
    print()
    print(f"失败 {len(fails)} 条")
    for name in fails:
        print("  ✘", name)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
