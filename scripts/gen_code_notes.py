"""Generate Obsidian code-structure notes under docs/code/ from src/mobile_crawler.

One note per module (file) listing its classes, public functions, and internal
imports as [[wikilinks]], plus "imported by" backlinks. One _index.md per package
keeps a hand-written summary (between the summary markers) across regenerations.

Usage: python scripts/gen_code_notes.py [--stage]
  --stage  git add docs/code after writing
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PKG = "mobile_crawler"
OUT = ROOT / "docs" / "code"
SUM_START, SUM_END = "<!-- summary:start -->", "<!-- summary:end -->"


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def note_path(mod: str, is_pkg: bool) -> str:
    """Vault-relative link target (no extension)."""
    rel = mod.removeprefix(PKG + ".").replace(".", "/") if mod != PKG else ""
    return f"code/{rel}/_index" if is_pkg else f"code/{rel}"


def first_line(doc: str | None) -> str:
    return doc.strip().splitlines()[0].strip() if doc and doc.strip() else ""


def resolve_import(node: ast.AST, mod: str, is_pkg: bool, known: set[str]) -> set[str]:
    names: list[str] = []
    if isinstance(node, ast.Import):
        names = [a.name for a in node.names]
    elif isinstance(node, ast.ImportFrom):
        if node.level:
            base = mod.split(".")
            base = base if is_pkg else base[:-1]
            base = base[: len(base) - (node.level - 1)]
            prefix = ".".join(base + ([node.module] if node.module else []))
        else:
            prefix = node.module or ""
        names = [prefix] + [f"{prefix}.{a.name}" for a in node.names]
    out = set()
    for n in names:
        if n in known:
            out.add(n)
    return out


def main() -> int:
    files = sorted((SRC / PKG).rglob("*.py"))
    info: dict[str, dict] = {}
    for f in files:
        mod = module_name(f)
        is_pkg = f.name == "__init__.py"
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        info[mod] = {
            "path": f.relative_to(ROOT).as_posix(),
            "is_pkg": is_pkg,
            "doc": first_line(ast.get_docstring(tree)),
            "classes": [n.name for n in tree.body if isinstance(n, ast.ClassDef)],
            "funcs": [
                n.name
                for n in tree.body
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and not n.name.startswith("_")
            ],
            "tree": tree,
        }
    known = set(info)
    imports: dict[str, set[str]] = {}
    for mod, d in info.items():
        deps: set[str] = set()
        for node in ast.walk(d["tree"]):
            if isinstance(node, ast.Import | ast.ImportFrom):
                deps |= resolve_import(node, mod, d["is_pkg"], known)
        # `from pkg import x` also yields pkg; drop self and prefer the deepest match
        deps.discard(mod)
        imports[mod] = deps
    imported_by: dict[str, set[str]] = defaultdict(set)
    for mod, deps in imports.items():
        for dep in deps:
            imported_by[dep].add(mod)

    def link(m: str) -> str:
        return f"[[{note_path(m, info[m]['is_pkg'])}|{m.removeprefix(PKG + '.') or PKG}]]"

    expected: set[Path] = set()

    def write(rel: str, text: str) -> None:
        p = ROOT / "docs" / (rel + ".md")
        expected.add(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")

    for mod, d in info.items():
        if d["is_pkg"]:
            continue  # package indexes are written below (they keep a hand-written summary)
        lines = [
            "---",
            "generated: true",
            f"file: {d['path']}",
            "---",
            f"# {mod}",
            "",
            d["doc"] or "_No module docstring._",
            "",
            f"Source: `{d['path']}`",
        ]
        if d["classes"]:
            lines += ["", "## Classes", *[f"- `{c}`" for c in d["classes"]]]
        if d["funcs"]:
            lines += ["", "## Functions", *[f"- `{n}`" for n in d["funcs"]]]
        if imports[mod]:
            lines += ["", "## Imports", *[f"- {link(m)}" for m in sorted(imports[mod])]]
        if imported_by[mod]:
            lines += ["", "## Imported by", *[f"- {link(m)}" for m in sorted(imported_by[mod])]]
        write(note_path(mod, d["is_pkg"]), "\n".join(lines) + "\n")

    # Package indexes: preserve hand-written summary between markers.
    pkgs = {m for m, d in info.items() if d["is_pkg"]}
    for pkg in pkgs:
        rel = note_path(pkg, True)
        p = ROOT / "docs" / (rel + ".md")
        summary = "_Add a one-line summary of this package here._"
        if p.exists():
            t = p.read_text(encoding="utf-8")
            if SUM_START in t and SUM_END in t:
                summary = t.split(SUM_START)[1].split(SUM_END)[0].strip()
        members = sorted(m for m in info if m != pkg and m.rsplit(".", 1)[0] == pkg)
        lines = [
            "---",
            "generated: partial",
            "---",
            f"# {pkg}",
            "",
            SUM_START,
            summary,
            SUM_END,
            "",
            "## Modules",
            *[f"- {link(m)}" + (f" - {info[m]['doc']}" if info[m]["doc"] else "") for m in members],
        ]
        write(rel, "\n".join(lines) + "\n")

    for p in OUT.rglob("*.md"):
        if p not in expected:
            p.unlink()
    for d in sorted(OUT.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    if "--stage" in sys.argv:
        subprocess.run(["git", "add", "-A", "docs/code"], cwd=ROOT, check=True)
    print(f"Wrote {len(expected)} notes to docs/code/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
