"""开发期工具：在内存中把检查更新源替换为指定 URL 后启动主界面（不修改源码）。

用法：
    python tools/dev_run_update_source.py [URL]
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/aeiexcenter-cell/"
    "CUPL-Auto-Essay-Formatter/port_to_macos/latest.json"
)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    url = args[0] if args else DEFAULT_SOURCE

    from essay_tool.platform_compat import ensure_ssl_certs
    import essay_tool.update_check as uc

    ensure_ssl_certs()
    uc.SOURCES = (url,)
    from essay_tool.gui.main_window import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
