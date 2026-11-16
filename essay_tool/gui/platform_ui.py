"""GUI 平台适配层（依赖 tkinter）：DPI 感知、缩放、图标、主题及 macOS 交互封装。"""

from __future__ import annotations

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
