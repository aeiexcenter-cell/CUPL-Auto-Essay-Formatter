"""GUI 平台适配层（依赖 tkinter）：DPI 感知、缩放、图标、主题及 macOS 交互封装。"""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from essay_tool.config.paths import resource_dir
from essay_tool.platform_compat import IS_MAC, IS_WIN, UI_MAC

MAC_TK_SCALING: float = 96.0 / 72.0


def enable_dpi_awareness() -> None:
    """Windows 下声明进程 DPI 感知；非 Windows 环境下空操作。"""
    if not IS_WIN:
        return
    try:
        import ctypes

        try:
            ok = ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            if ok:
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            hr = ctypes.windll.shcore.SetProcessDpiAwareness(1)
            if hr == 0:
                return
        except Exception:  # noqa: BLE001
            pass
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


def apply_platform_scaling(root: tk.Misc) -> None:
    """按平台校准 Tk scaling（必须在创建子控件/字体前调用）。"""
    try:
        if IS_MAC:
            root.tk.call("tk", "scaling", MAC_TK_SCALING)
            return
        dpi = root.winfo_fpixels("1i")
        if dpi > 0:
            root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:  # noqa: BLE001
        pass


def init_theme(root: tk.Misc) -> None:
    """macOS（含界面预览模式）下切到 clam 主题以保留自定义配色与间距。"""
    if not UI_MAC:
        return
    try:
        ttk.Style(root).theme_use("clam")
    except Exception:  # noqa: BLE001
        pass


def apply_app_icon(win: tk.Misc) -> None:
    """设置窗口/应用图标；缺失或失败时静默沿用默认图标。"""
    assets_dir = resource_dir() / "essay_tool" / "gui" / "assets"
    try:
        if IS_WIN:
            win.iconbitmap(default=str(assets_dir / "app.ico"))
        else:
            img = tk.PhotoImage(file=str(assets_dir / "app.png"), master=win)
            win._app_icon_ref = img  # type: ignore[attr-defined]
            win.iconphoto(True, img)
    except Exception:  # noqa: BLE001
        pass


class _MacFlatButton(tk.Label):
    """在 macOS Aqua/clam 下用 Label 模拟自定义底色的扁平文字按钮。"""

    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        self._cmd = kwargs.pop("command", None)
        activebg = kwargs.pop("activebackground", None)
        self._btn_state = str(kwargs.get("state", "normal"))
        self._normal_bg = kwargs.get("bg", kwargs.get("background"))
        self._active_bg = activebg if activebg is not None else self._normal_bg
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _event=None) -> None:
        if self._btn_state != "disabled" and self._active_bg is not None:
            super().configure(bg=self._active_bg)

    def _on_leave(self, _event=None) -> None:
        if self._normal_bg is not None:
            super().configure(bg=self._normal_bg)

    def _on_release(self, event) -> None:
        if self._btn_state == "disabled":
            return
        if 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()

    def invoke(self):
        if self._btn_state != "disabled" and self._cmd is not None:
            return self._cmd()
        return None

    def configure(self, cnf=None, **kw):
        if cnf:
            kw = {**cnf, **kw}
        if not kw:
            return super().configure()
        if "command" in kw:
            self._cmd = kw.pop("command")
        if "activebackground" in kw:
            self._active_bg = kw.pop("activebackground")
        if "state" in kw:
            self._btn_state = str(kw["state"])
        if "bg" in kw:
            self._normal_bg = kw["bg"]
        elif "background" in kw:
            self._normal_bg = kw["background"]
        if kw:
            return super().configure(**kw)
        return None

    config = configure


def flat_button(parent: tk.Misc, **kwargs) -> tk.Widget:
    """扁平带底色按钮：Windows 返回原生 tk.Button，macOS/预览模式返回模拟 Label。"""
    if not UI_MAC:
        return tk.Button(parent, **kwargs)
    return _MacFlatButton(parent, **kwargs)


def bind_shortcut(widget: tk.Misc, key: str, fn: Callable, *, all_: bool = False) -> None:
    """绑定 Ctrl（Windows/通用）以及在 macOS 上额外绑定 Command 快捷键。"""
    binder = widget.bind_all if all_ else widget.bind
    for mod in ("Control", "Command") if IS_MAC else ("Control",):
        for ch in (key.lower(), key.upper()):
            binder(f"<{mod}-{ch}>", fn)


def unbind_shortcut(widget: tk.Misc, key: str, *, all_: bool = False) -> None:
    """解绑由 `bind_shortcut` 注册的快捷键。"""
    unbinder = widget.unbind_all if all_ else widget.unbind
    for mod in ("Control", "Command") if IS_MAC else ("Control",):
        for ch in (key.lower(), key.upper()):
            try:
                unbinder(f"<{mod}-{ch}>")
            except tk.TclError:
                pass


def bind_context_menu(widget: tk.Misc, fn: Callable) -> None:
    """绑定右键菜单（macOS 兼容双指点按 Button-2/Button-3 与 Control+左键）。"""
    widget.bind("<Button-3>", fn)
    if IS_MAC:
        widget.bind("<Button-2>", fn)
        widget.bind("<Control-Button-1>", fn)


_MAC_TEXT_REPLACEMENTS = (
    ("%APPDATA%\\AutoEssayTypesettingTool", "~/Library/Application Support/AutoEssayTypesettingTool"),
    ("资源管理器", "访达"),
    ("Ctrl+Z", "⌘Z"),
    ("Ctrl+C", "⌘C"),
    ("Ctrl+A", "⌘A"),
    ("Ctrl+Enter", "⌘Enter"),
    ("Ctrl＋", "⌘＋"),
    ("Ctrl+", "⌘"),
    ("Ctrl/", "⌘/"),
    ("按住 Ctrl ", "按住 ⌘ "),
)


def platform_text(text: str) -> str:
    """按 UI 平台把 Windows 专属文案/快捷键标识替换成 macOS 习惯表述。"""
    if not UI_MAC:
        return text
    out = text
    for src, dst in _MAC_TEXT_REPLACEMENTS:
        out = out.replace(src, dst)
    return out


def install_mac_handlers(
    root: tk.Tk,
    *,
    on_quit: Callable[[], None] | None = None,
    on_open_files: Callable[[list[str]], None] | None = None,
    on_about: Callable[[], None] | None = None,
) -> bool:
    """在 macOS 下注册系统级 ⌘Q、Dock 打开文件与关于菜单回调。"""
    if not IS_MAC:
        return False
    try:
        if on_quit is not None:
            root.createcommand("::tk::mac::Quit", lambda *_a: on_quit())
        if on_open_files is not None:
            def _open_doc(*args: str) -> None:
                paths = [str(a) for a in args if a]
                if paths:
                    on_open_files(paths)

            root.createcommand("::tk::mac::OpenDocument", _open_doc)
        if on_about is not None:
            root.createcommand("tkAboutDialog", lambda *_a: on_about())
        return True
    except Exception:  # noqa: BLE001
        return False
