"""用当前仓库的更新源测试检查更新模块（不修改原 update_check.py 与 latest.json）。

用法：
    python tools/check_update_live.py
    python tools/check_update_live.py --source https://...
"""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/aeiexcenter-cell/"
    "CUPL-Auto-Essay-Formatter/port_to_macos/latest.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="测试从指定更新源拉取并解析 latest.json")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="latest.json 地址")
    args = parser.parse_args(argv)

    from essay_tool import __version__, update_check as uc
    from essay_tool.platform_compat import ensure_ssl_certs

    ensure_ssl_certs()
    info = uc.fetch_latest(__version__, sources=(args.source,))
    if info is None:
        print(f"FAIL  无法从更新源读取合格的 latest.json：{args.source}")
        return 1
    if not info.version or not info.downloads:
        print(f"FAIL  解析结果缺少版本号或下载链接：{info}")
        return 1

    print(f"OK    更新源可访问：{args.source}")
    print(f"      最新版本号：{info.version}（日期 {info.display_date()}，链接数 {len(info.downloads)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
