#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
    if command -v python3.13 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3.13)"
    else
        PYTHON_BIN="$(command -v python3)"
    fi
fi

VENV="$ROOT/packaging/.venv-macos"
PY="$VENV/bin/python"
if [ ! -x "$PY" ]; then
    "$PYTHON_BIN" -m venv "$VENV"
fi
"$PY" -m pip install --retries 8 --timeout 60 --disable-pip-version-check -q -r "$ROOT/requirements-build.txt"

"$PY" "$ROOT/tools/update_integrity.py"

DIST="$ROOT/dist"
WORK="$ROOT/build/pyinstaller"
rm -rf "$DIST/CUPL-UTAF" "$DIST/CUPL-UTAF.app" "$WORK"
mkdir -p "$DIST" "$WORK"

"$PY" -m PyInstaller --noconfirm --clean --distpath "$DIST" --workpath "$WORK" \
    "$ROOT/packaging/CUPL-UTAF-macos.spec"

APP="$DIST/CUPL-UTAF.app"
EXE="$APP/Contents/MacOS/CUPL-UTAF"
if [ ! -x "$EXE" ]; then
    echo "FAILED: $EXE not produced" >&2
    exit 1
fi

REPORT="$WORK/selftest.txt"
STDLOG="$WORK/selftest_stdio.log"
rm -f "$REPORT" "$STDLOG"
set +e
"$EXE" --selftest "$REPORT" >"$STDLOG" 2>&1
RC=$?
set -e
if [ -s "$STDLOG" ]; then
    echo "=== selftest stdio ==="
    cat "$STDLOG"
fi
if [ -f "$REPORT" ]; then
    echo "=== selftest report ==="
    cat "$REPORT"
fi
if [ "$RC" -ne 0 ]; then
    MSG="$(cat "$REPORT" "$STDLOG" 2>/dev/null | grep -v '^OK ' | tr '\n' ' ' | cut -c1-1500)"
    echo "::error title=SelftestFailed::exit=${RC} ${MSG}"
    exit "$RC"
fi

"$PY" "$ROOT/packaging/make_notices.py" --platform macos

codesign --force --deep -s - "$APP"

VER="$("$PY" -c "from essay_tool import __version__; print(__version__)")"
ARCH="$(uname -m)"
DMG_ROOT="$ROOT/build/dmg-root"
rm -rf "$DMG_ROOT"
mkdir -p "$DMG_ROOT"
cp -R "$APP" "$DMG_ROOT/CUPL-UTAF.app"
ln -s /Applications "$DMG_ROOT/Applications"
cp -R "$ROOT/build/licenses" "$DMG_ROOT/licenses"

DMG_PATH="$DIST/CUPL-UTAF V${VER} macOS-${ARCH}.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "CUPL-UTAF V${VER}" -srcfolder "$DMG_ROOT" -ov -format UDZO "$DMG_PATH"
echo "Built: $DMG_PATH"
