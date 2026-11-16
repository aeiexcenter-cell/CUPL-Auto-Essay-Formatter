"""GUI 巡检与自动截图脚本：遍历全部页签、检查文字截断并尝试截图。

用法：
    python tools/gui_tour.py <输出目录> [--doc <docx路径>]
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAB_SLUG = {
    "文件": "file",
    "页面": "page",
    "格式": "format",
    "结构": "structure",
    "封面": "cover",
    "关于": "about",
}


def _pump(app: tk.Tk, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.update_idletasks()
        app.update()
        time.sleep(0.02)
    app.update_idletasks()
    app.update()


def _scan_truncation(root: tk.Misc) -> list[str]:
    hits: list[str] = []

    def walk(w: tk.Misc) -> None:
        try:
            viewable = bool(w.winfo_viewable())
        except tk.TclError:
            return
        if viewable and isinstance(w, (tk.Label, tk.Button, ttk.Checkbutton)):
            try:
                wrap = int(str(w.cget("wraplength"))) if "wraplength" in w.keys() else 0
            except Exception:  # noqa: BLE001
                wrap = 0
            if wrap <= 0:
                req_w = w.winfo_reqwidth()
                cur_w = w.winfo_width()
                if cur_w > 1 and req_w > cur_w + 4:
                    txt = str(w.cget("text") or "").replace("\n", " ")[:40]
                    hits.append(f"{w.winfo_path(w)} req={req_w} actual={cur_w} text={txt!r}")
        for child in w.winfo_children():
            walk(child)

    walk(root)
    return hits


def run_tour(out_dir: pathlib.Path, doc_path: pathlib.Path | None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    dialog_logs: list[str] = []

    orig_boxes = {
        name: getattr(messagebox, name)
        for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel")
    }
    messagebox.showinfo = lambda t="", m="", **_kw: (dialog_logs.append(f"info:{t}:{m}"), "ok")[1]
    messagebox.showwarning = lambda t="", m="", **_kw: (dialog_logs.append(f"warn:{t}:{m}"), "ok")[1]
    messagebox.showerror = lambda t="", m="", **_kw: (dialog_logs.append(f"err:{t}:{m}"), "ok")[1]
    messagebox.askyesno = lambda t="", m="", **_kw: (dialog_logs.append(f"yesno:{t}:{m}"), True)[1]
    messagebox.askokcancel = lambda t="", m="", **_kw: (dialog_logs.append(f"okcancel:{t}:{m}"), True)[1]

    from essay_tool.config.paths import cleanup_session_work_dir
    from essay_tool.gui import main_window as mw

    report_lines: list[str] = []
    trunc_lines: list[str] = []
    app = None
    try:
        app = mw.MainWindow()
        _pump(app, 0.25)

        if doc_path is not None:
            resolved = doc_path.resolve()
            app._on_files_dropped([str(resolved)])
            _pump(app, 0.35)
            report_lines.append(f"import_doc: {resolved.name} -> doc_path={app.doc_path}")

        tab_ids = list(app.nb.tabs())
        for i, tab_id in enumerate(tab_ids):
            label = str(app.nb.tab(tab_id, "text"))
            slug = TAB_SLUG.get(label, f"tab{i}")
            app.nb.select(i)
            _pump(app, 0.40)

            truncs = _scan_truncation(app)
            if truncs:
                trunc_lines.append(f"=== tab_{i}_{slug} ({label}) ===")
                trunc_lines.extend(truncs)

            shot_status = "ok"
            shot_path = out_dir / f"tab_{i}_{slug}.png"
            try:
                from PIL import ImageGrab

                img = ImageGrab.grab()
                img.save(shot_path)
            except Exception as exc:  # noqa: BLE001
                shot_status = f"skipped ({type(exc).__name__}: {exc})"

            extra = ""
            if label == "结构":
                extra = f" adjust_ready={app._adjust_instance is not None}"
            report_lines.append(
                f"tab_{i}_{slug} ({label}): trunc={len(truncs)} screenshot={shot_status}{extra}"
            )

        if dialog_logs:
            report_lines.append(f"dialogs_suppressed: {len(dialog_logs)}")
            report_lines.extend(f"  - {d[:120]}" for d in dialog_logs[:10])
    finally:
        for name, fn in orig_boxes.items():
            setattr(messagebox, name, fn)
        if app is not None:
            try:
                app.destroy()
            except Exception:  # noqa: BLE001
                pass
        cleanup_session_work_dir()

    (out_dir / "tour_report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    (out_dir / "truncation.txt").write_text(
        ("\n".join(trunc_lines) if trunc_lines else "无控件文字截断。") + "\n",
        encoding="utf-8",
    )
    print("\n".join(report_lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GUI 页签巡检与自动截图")
    parser.add_argument("out_dir", type=pathlib.Path, help="截图与报告输出目录")
    parser.add_argument("--doc", type=pathlib.Path, default=None, help="可选测试文档路径")
    args = parser.parse_args(argv)
    return run_tour(args.out_dir, args.doc)


if __name__ == "__main__":
    raise SystemExit(main())
