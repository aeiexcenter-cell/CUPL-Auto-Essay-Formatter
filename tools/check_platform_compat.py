"""平台兼容层与跨平台 GUI 适配的回归检查。

用法：.venv\\Scripts\\python.exe tools\\check_platform_compat.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

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


def case_paths() -> None:
    print("== paths.user_data_dir ==")
    from essay_tool.config import paths

    with tempfile.TemporaryDirectory() as tmp:
        home = pathlib.Path(tmp) / "home"
        legacy = home / ".config" / paths.APP_DIR_NAME / "presets"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "custom.json").write_text("old", encoding="utf-8")

        target = paths.user_data_dir(platform="darwin", env={}, home=home)
        expected_mac = home / "Library" / "Application Support" / paths.APP_DIR_NAME
        check("darwin 迁移目录位置正确", target == expected_mac, repr(target))
        check(
            "darwin 旧目录迁移至新目录",
            (target / "presets" / "custom.json").read_text(encoding="utf-8") == "old",
        )

        # 新旧并存时不覆盖新目录
        (target / "presets" / "custom.json").write_text("new", encoding="utf-8")
        (legacy / "custom.json").write_text("old-again", encoding="utf-8")
        target2 = paths.user_data_dir(platform="darwin", env={}, home=home)
        check(
            "darwin 新旧并存不覆盖新目录",
            (target2 / "presets" / "custom.json").read_text(encoding="utf-8") == "new",
        )

        roaming = pathlib.Path(tmp) / "Roaming"
        win_dir = paths.user_data_dir(platform="win32", env={"APPDATA": str(roaming)}, home=home)
        check("win32 user_data_dir", win_dir == roaming / paths.APP_DIR_NAME, repr(win_dir))


def case_ui_basics() -> None:
    print("== platform_ui 基础 ==")
    import tkinter as tk
    from tkinter import ttk
    from essay_tool.gui import platform_ui

    root = tk.Tk()
    root.withdraw()
    orig_ui_mac = platform_ui.UI_MAC
    try:
        before_theme = ttk.Style(root).theme_use()
        platform_ui.UI_MAC = False
        platform_ui.init_theme(root)
        check("Windows 默认不改变 ttk 主题", ttk.Style(root).theme_use() == before_theme)

        platform_ui.UI_MAC = True
        platform_ui.init_theme(root)
        check("UI_MAC=True 切换到 clam 主题", ttk.Style(root).theme_use() == "clam")

        platform_ui.apply_app_icon(root)
        check("apply_app_icon 不抛异常", True)
    finally:
        platform_ui.UI_MAC = orig_ui_mac
        root.destroy()


def case_flat_button() -> None:
    print("== flat_button ==")
    import tkinter as tk
    from essay_tool.gui import platform_ui

    root = tk.Tk()
    root.withdraw()
    orig_ui_mac = platform_ui.UI_MAC
    try:
        platform_ui.UI_MAC = False
        clicked: list[str] = []
        w_win = platform_ui.flat_button(
            root,
            text="收起日志",
            bd=0,
            bg="#e9e9e6",
            fg="#8a8a8a",
            activebackground="#e9e9e6",
            command=lambda: clicked.append("win"),
        )
        check("Windows 返回 tk.Button", isinstance(w_win, tk.Button) and w_win.cget("bg") == "#e9e9e6")

        platform_ui.UI_MAC = True
        w_mac = platform_ui.flat_button(
            root,
            text="收起日志",
            bd=0,
            bg="#e9e9e6",
            fg="#8a8a8a",
            activebackground="#d6d6d1",
            command=lambda: clicked.append("mac"),
        )
        check("UI_MAC 返回 tk.Label 子类", isinstance(w_mac, tk.Label))
        w_mac.invoke()
        check("UI_MAC flat_button invoke 触发回调", clicked == ["mac"], repr(clicked))
        w_mac.configure(state="disabled")
        w_mac.invoke()
        check("disabled 后 invoke 不触发回调", clicked == ["mac"], repr(clicked))
        w_mac.configure(text="展开日志")
        check("configure 更新文本", w_mac.cget("text") == "展开日志")
    finally:
        platform_ui.UI_MAC = orig_ui_mac
        root.destroy()


def case_bindings() -> None:
    print("== 快捷键 / 右键 / 文案 / macHandlers ==")
    import tkinter as tk
    from essay_tool.gui import platform_ui

    root = tk.Tk()
    root.withdraw()
    orig_ui_mac = platform_ui.UI_MAC
    orig_is_mac = platform_ui.IS_MAC
    try:
        frame = tk.Frame(root)
        if not platform_ui.IS_MAC:
            platform_ui.bind_shortcut(frame, "z", lambda _e: None)
            bound = frame.bind()
            check(
                "Windows bind_shortcut 绑 Control 且无 Command",
                any("Control" in b and "z" in b.lower() for b in bound)
                and not any("Command" in b for b in bound),
                repr(bound),
            )
            platform_ui.unbind_shortcut(frame, "z")
        else:
            platform_ui.bind_shortcut(frame, "z", lambda _e: None)
            bound = frame.bind()
            check("macOS bind_shortcut 含 Command", any("Command" in b for b in bound), repr(bound))
            platform_ui.unbind_shortcut(frame, "z")

        sample = "右键：插入空行；Ctrl+Z：撤回上一步。Ctrl＋滚轮缩放，资源管理器，%APPDATA%\\AutoEssayTypesettingTool"
        platform_ui.UI_MAC = False
        check("Windows 文案原样返回", platform_ui.platform_text(sample) == sample)
        platform_ui.UI_MAC = True
        mac_txt = platform_ui.platform_text(sample)
        check(
            "UI_MAC 文案替换为 Mac 习惯",
            "⌘Z" in mac_txt and "⌘＋" in mac_txt and "访达" in mac_txt and "Library/Application Support" in mac_txt,
            mac_txt,
        )

        # install_mac_handlers 在非 Mac 返回 False；模拟 Mac 时能注册 Tcl 命令
        platform_ui.IS_MAC = False
        check("非 Mac install_mac_handlers 返回 False", platform_ui.install_mac_handlers(root) is False)

        opened: list[list[str]] = []
        quitted: list[bool] = []
        platform_ui.IS_MAC = True
        ok = platform_ui.install_mac_handlers(
            root,
            on_quit=lambda: quitted.append(True),
            on_open_files=lambda ps: opened.append(ps),
            on_about=lambda: None,
        )
        quit_cmd = str(root.tk.call("info", "commands", "::tk::mac::Quit"))
        root.tk.call("::tk::mac::OpenDocument", "/tmp/a.docx")
        root.tk.call("::tk::mac::Quit")
        check(
            "模拟 Mac 注册 ::tk::mac 命令并可触发",
            ok is True and "::tk::mac::Quit" in quit_cmd and opened == [["/tmp/a.docx"]] and quitted == [True],
            f"quit_cmd={quit_cmd!r} opened={opened!r} quitted={quitted!r}",
        )
    finally:
        platform_ui.UI_MAC = orig_ui_mac
        platform_ui.IS_MAC = orig_is_mac
        root.destroy()


def main() -> int:
    case_compat()
    case_paths()
    case_ui_basics()
    case_flat_button()
    case_bindings()
    print()
    print(f"失败 {len(fails)} 条")
    for name in fails:
        print("  ✘", name)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
