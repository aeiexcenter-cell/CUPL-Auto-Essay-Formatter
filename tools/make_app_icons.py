"""从 app.ico 生成 macOS/跨平台使用的 app.png（512px）与 app.icns。

用法：.venv\\Scripts\\python.exe tools\\make_app_icons.py
"""

from __future__ import annotations

import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "essay_tool" / "gui" / "assets"
SRC_ICO = ASSETS / "app.ico"
OUT_PNG = ASSETS / "app.png"
OUT_ICNS = ASSETS / "app.icns"


def main() -> int:
    with Image.open(SRC_ICO) as im:
        sizes = im.info.get("sizes")
        if sizes:
            im.size = max(sizes)
        rgba = im.convert("RGBA")
        im512 = rgba.resize((512, 512), Image.Resampling.LANCZOS)
        im512.save(OUT_PNG, format="PNG")
        im512.save(OUT_ICNS, format="ICNS")
    print(f"已生成：{OUT_PNG.name}、{OUT_ICNS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
