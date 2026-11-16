"""跨平台兼容层（无 tkinter 依赖，引擎/配置/界面均可使用）。"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from collections.abc import Mapping


def _resolve(platform: str, env: Mapping[str, str]) -> dict[str, object]:
    """根据平台标识与环境变量解析跨平台 UI/行为常量。"""
    is_win = platform == "win32"
    is_mac = platform == "darwin"
    preview_mac = env.get("ESSAY_TOOL_UI_PREVIEW", "").strip().lower() == "mac"
    ui_mac = is_mac or preview_mac
    # Windows 上没有苹方字体，UI 预览模式只切换界面样式，不替换字体族
    ui_font = "PingFang SC" if is_mac else "Microsoft YaHei UI"
    mod_key = "Command" if ui_mac else "Control"
    mod_label = "⌘" if ui_mac else "Ctrl"
    return {
        "IS_WIN": is_win,
        "IS_MAC": is_mac,
        "UI_MAC": ui_mac,
        "UI_FONT": ui_font,
        "MOD_KEY": mod_key,
        "MOD_LABEL": mod_label,
    }


_RESOLVED = _resolve(sys.platform, os.environ)
IS_WIN: bool = bool(_RESOLVED["IS_WIN"])
IS_MAC: bool = bool(_RESOLVED["IS_MAC"])
UI_MAC: bool = bool(_RESOLVED["UI_MAC"])
UI_FONT: str = str(_RESOLVED["UI_FONT"])
MOD_KEY: str = str(_RESOLVED["MOD_KEY"])
MOD_LABEL: str = str(_RESOLVED["MOD_LABEL"])


def user_data_base(
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
    home: pathlib.Path | None = None,
) -> pathlib.Path:
    """返回每用户可写数据目录的父级根目录。"""
    plat = sys.platform if platform is None else platform
    environ = os.environ if env is None else env
    h = pathlib.Path.home() if home is None else home
    if plat == "darwin":
        return h / "Library" / "Application Support"
    base = environ.get("APPDATA")
    return pathlib.Path(base) if base else h / ".config"


def open_path(path: os.PathLike | str) -> None:
    """在系统默认文件管理器或关联程序中打开路径，失败时统一抛 OSError。"""
    target = str(path)
    if IS_WIN:
        os.startfile(target)  # noqa: S606
        return
    cmd = ["open", target] if IS_MAC else ["xdg-open", target]
    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise OSError(str(exc)) from exc


def ensure_ssl_certs() -> bool:
    """在 macOS 下确保 Python HTTPS 默认上下文可找到 CA 证书包。"""
    if not IS_MAC:
        return False
    existing = os.environ.get("SSL_CERT_FILE")
    if existing and os.path.isfile(existing):
        return True
    try:
        import certifi

        where = certifi.where()
        if where and os.path.isfile(where):
            os.environ["SSL_CERT_FILE"] = where
            return True
    except Exception:  # noqa: BLE001
        return False
    return False
