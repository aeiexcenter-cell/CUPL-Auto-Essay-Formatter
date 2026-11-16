"""跨平台输出一致性检查：对比 Windows 与 macOS 下排版引擎输出的 docx 部件字节。

用法：
    python tools/check_parity.py generate <输出目录>
    python tools/check_parity.py compare <目录A> <目录B>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES = (
    ROOT / "samples" / "sample.txt",
    ROOT / "Adversarial Automatic Test" / "_fixtures" / "手打目录无页码.docx",
    ROOT / "Adversarial Automatic Test" / "_fixtures" / "手打目录无页码-完整.docx",
)

_CORE_TS_RE = re.compile(
    rb"<dcterms:(created|modified)\b[^>]*>.*?</dcterms:\1>",
    re.DOTALL,
)


def _normalize_part(name: str, data: bytes) -> bytes:
    if name == "docProps/core.xml":
        return _CORE_TS_RE.sub(b"", data)
    return data


def generate(out_dir: pathlib.Path) -> int:
    from essay_tool.config import paths
    from essay_tool.config.preset_io import load_preset
    from essay_tool.engine import cover, pipeline
    from essay_tool.engine.alerts import AlertCollector
    from essay_tool.engine.template import build_template

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    presets = sorted(paths.builtin_presets_dir().glob("*.json"))
    assert len(presets) >= 4, f"内置预设不足 4 份：{len(presets)}"
    for src in SOURCES:
        assert src.is_file(), f"缺少输入夹具：{src}"

    manifest: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="aet-parity-") as tmp:
        tmp_root = pathlib.Path(tmp)
        for s_idx, src in enumerate(SOURCES):
            for p_idx, preset in enumerate(presets):
                work_dir = tmp_root / f"w_{s_idx}_{p_idx}"
                work_dir.mkdir(parents=True, exist_ok=True)
                out_docx = pipeline.run(src, preset, work_dir, alerts=AlertCollector())
                name = f"pipeline_{s_idx}_{p_idx}.docx"
                shutil.copy2(out_docx, out_dir / name)
                manifest[name] = f"{src.name} + {preset.name}"

        fields = cover.CoverFields(
            title="测试题目",
            student_name="张三",
            student_id="20220001",
            college="法学院",
            major="法学",
            grade="2022",
            advisor_name="李四",
            course_name="民法总论",
            course_code="101",
            course_seq="1",
            teacher_name="王五",
            session="二十四",
        )
        for name, fn in (
            ("cover_thesis.docx", cover.build_thesis_cover_document),
            ("cover_course.docx", cover.build_course_cover_document),
            ("cover_tenstar.docx", cover.build_tenstar_cover_document),
        ):
            doc = fn(fields)
            doc.save(str(out_dir / name))
            manifest[name] = fn.__name__

        tpl_work = tmp_root / "tpl_work"
        tpl_work.mkdir(parents=True, exist_ok=True)
        cfg = load_preset(presets[0])
        build_template(
            None,
            out_dir / "blank_template.docx",
            work_dir=tpl_work,
            with_cover=True,
            preset_config=cfg,
        )
        manifest["blank_template.docx"] = f"template({presets[0].name})"

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已生成 {len(manifest)} 份产物到：{out_dir}")
    return 0


def compare(dir_a: pathlib.Path, dir_b: pathlib.Path) -> int:
    files_a = {p.name for p in dir_a.glob("*.docx")}
    files_b = {p.name for p in dir_b.glob("*.docx")}
    if files_a != files_b or not files_a:
        print(f"FAIL  文件集合不一致：仅A={sorted(files_a - files_b)}，仅B={sorted(files_b - files_a)}")
        return 1

    bad = 0
    for name in sorted(files_a):
        pa, pb = dir_a / name, dir_b / name
        diffs: list[str] = []
        with zipfile.ZipFile(pa) as za, zipfile.ZipFile(pb) as zb:
            na, nb = set(za.namelist()), set(zb.namelist())
            if na != nb:
                diffs.append(f"部件集合不一致 仅A={sorted(na - nb)} 仅B={sorted(nb - na)}")
            for part in sorted(na & nb):
                ba = _normalize_part(part, za.read(part))
                bb = _normalize_part(part, zb.read(part))
                if ba != bb:
                    diffs.append(f"{part}({len(ba)} vs {len(bb)})")
        if diffs:
            bad += 1
            print(f"FAIL  {name}: " + "; ".join(diffs))
        else:
            print(f"OK    {name}")

    print(f"共对比 {len(files_a)} 份，差异 {bad} 份")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="跨平台输出一致性检查")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_gen = sub.add_parser("generate", help="生成基准产物")
    p_gen.add_argument("out_dir", type=pathlib.Path)
    p_cmp = sub.add_parser("compare", help="对比两份产物目录")
    p_cmp.add_argument("dir_a", type=pathlib.Path)
    p_cmp.add_argument("dir_b", type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.cmd == "generate":
        return generate(args.out_dir)
    return compare(args.dir_a, args.dir_b)


if __name__ == "__main__":
    raise SystemExit(main())
