# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置（macOS .app：onedir + BUNDLE）。

用法：在 macOS 上运行 `bash packaging/build_macos.sh`。
"""

import pathlib
import sys

ROOT = pathlib.Path(SPECPATH).resolve().parent          # noqa: F821
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import update_integrity                                   # noqa: E402
from essay_tool import __version__                        # noqa: E402

APP_NAME = "CUPL-UTAF"
ICON = str(ROOT / "essay_tool" / "gui" / "assets" / "app.icns")

datas = []
for _label, pattern in update_integrity.PATTERNS:
    found = sorted(p for p in (ROOT / "reference").glob(pattern) if not p.name.startswith("~$"))
    if not found:
        raise SystemExit(f"打包失败：reference/ 里找不到「{_label}」（{pattern}）")
    datas.append((str(found[0]), "reference"))
for p in sorted((ROOT / "presets").glob("*.json")):
    datas.append((str(p), "presets"))
for p in sorted((ROOT / "essay_tool" / "gui" / "assets").iterdir()):
    datas.append((str(p), "essay_tool/gui/assets"))

a = Analysis(                                             # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=["certifi"],
    excludes=["fitz", "pymupdf", "win32com", "win32api", "win32con", "pythoncom",
              "pywintypes", "numpy", "matplotlib", "pytest", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)                                         # noqa: F821
exe = EXE(                                                # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    argv_emulation=False,
    icon=ICON,
    upx=False,
)
coll = COLLECT(                                           # noqa: F821
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name=APP_NAME,
)
app = BUNDLE(                                             # noqa: F821
    coll,
    name="CUPL-UTAF.app",
    icon=ICON,
    bundle_identifier="io.github.aeiexcenter-cell.cupl-utaf",
    version=__version__,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": "CUPL本科论文自动排版工具",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": True,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Word Document",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "CFBundleTypeExtensions": ["docx"],
                "LSItemContentTypes": ["org.openxmlformats.wordprocessingml.document"],
            },
            {
                "CFBundleTypeName": "Plain Text",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "CFBundleTypeExtensions": ["txt"],
                "LSItemContentTypes": ["public.plain-text"],
            },
        ],
    },
)
