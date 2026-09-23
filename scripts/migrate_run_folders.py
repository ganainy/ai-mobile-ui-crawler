"""Move old run folders to the layout where every report sits under ``reports/`` (issue #26).

Usage (through the project venv)::

    .venv312/Scripts/python.exe scripts/migrate_run_folders.py            # migrate
    .venv312/Scripts/python.exe scripts/migrate_run_folders.py --dry-run  # only list what would change
    .venv312/Scripts/python.exe scripts/migrate_run_folders.py --base PATH

Per ``run_*`` folder under ``output_data/``:

- ``reports/report_run_<id>.html``   -> ``reports/run_report.html``
- ``reports/report_run_<id>.json``   -> deleted (the Analysis Bundle replaced it)
- ``reports/<hash>_report.json|pdf`` -> ``reports/mobsf/``
- ``analysis/*``                     -> ``reports/analysis/``
- ``data/config_snapshot.json``      -> ``reports/config_snapshot.json``
- ``logs/crawler_trace.jsonl`` (or the older ``droidrun_trace.jsonl``) -> ``reports/crawler_trace.jsonl``
- any other file in ``data/`` or ``logs/`` -> ``reports/`` under its own name
- ``analysis/``, ``data/`` and ``logs/`` are removed once empty

Screenshots, PCAP, videos and APKs stay put, so the HTML's ``../screenshots/`` links and the
bundle's run-folder-relative screenshot paths still resolve. Existing targets are never
overwritten (the source is left and reported as skipped); running it twice changes nothing.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mobile_crawler.domain.run_folder_layout import RunFolderLayout  # noqa: E402

_MOBSF_REPORT = re.compile(r"^[0-9a-f]{32}_report\.(json|pdf)$")
_LEGACY_DIRS = ("analysis", "data", "logs")


@dataclass(frozen=True)
class Action:
    kind: str  # "move" | "delete" | "skip" | "rmdir"
    source: Path
    target: Path | None = None

    def __str__(self) -> str:
        if self.kind == "move":
            return f"move   {self.source} -> {self.target}"
        if self.kind == "skip":
            return f"skip   {self.source} (target exists: {self.target})"
        return f"{self.kind:<6} {self.source}"


def _planned_moves(run: Path) -> tuple[list[tuple[Path, Path]], list[Path]]:
    """(source, target) moves in priority order, plus files to delete."""
    layout = RunFolderLayout(run)
    reports = layout.reports_dir
    moves: list[tuple[Path, Path]] = []
    deletes: list[Path] = []

    if reports.is_dir():
        for f in sorted(p for p in reports.iterdir() if p.is_file()):
            if f.name.startswith("report_run_") and f.suffix == ".html":
                moves.append((f, layout.run_report_html))
            elif f.name.startswith("report_run_") and f.suffix == ".json":
                deletes.append(f)
            elif _MOBSF_REPORT.match(f.name):
                moves.append((f, layout.mobsf_dir / f.name))

    analysis = run / "analysis"
    if analysis.is_dir():
        for f in sorted(p for p in analysis.rglob("*") if p.is_file()):
            moves.append((f, layout.analysis_dir / f.relative_to(analysis)))

    for name, target in (
        ("data/config_snapshot.json", layout.config_snapshot),
        ("logs/crawler_trace.jsonl", layout.crawler_trace),
        ("logs/droidrun_trace.jsonl", layout.crawler_trace),
    ):
        if (run / name).is_file():
            moves.append((run / name, target))

    already = {src for src, _ in moves}
    for folder in ("data", "logs"):
        if (run / folder).is_dir():
            for f in sorted(p for p in (run / folder).rglob("*") if p.is_file()):
                if f not in already:
                    moves.append((f, reports / f.name))

    return moves, deletes


def migrate_run_folder(run: Path, dry_run: bool = False) -> list[Action]:
    """Migrate one run folder in place; returns what was (or, on dry run, would be) done."""
    run = Path(run)
    moves, deletes = _planned_moves(run)

    actions: list[Action] = []
    taken: set[Path] = set()
    leaving: set[Path] = set(deletes)
    for source, target in moves:
        if target.exists() or target in taken:
            actions.append(Action("skip", source, target))
            continue
        taken.add(target)
        leaving.add(source)
        actions.append(Action("move", source, target))
    actions.extend(Action("delete", f) for f in deletes)

    for name in _LEGACY_DIRS:
        folder = run / name
        if folder.is_dir() and all(f in leaving for f in folder.rglob("*") if f.is_file()):
            actions.append(Action("rmdir", folder))

    if dry_run:
        return actions

    for action in actions:
        if action.kind == "move":
            action.target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(action.source, action.target)
        elif action.kind == "delete":
            action.source.unlink()
        elif action.kind == "rmdir":
            _remove_empty_tree(action.source)
    return actions


def _remove_empty_tree(folder: Path) -> None:
    for sub in sorted((p for p in folder.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        sub.rmdir()
    folder.rmdir()


def migrate_all(base: Path, dry_run: bool = False) -> dict[Path, list[Action]]:
    """Migrate every ``run_*`` folder directly under ``base``; only folders with changes are returned."""
    results: dict[Path, list[Action]] = {}
    for run in sorted(p for p in Path(base).iterdir() if p.is_dir() and p.name.startswith("run_")):
        actions = migrate_run_folder(run, dry_run=dry_run)
        if actions:
            results[run] = actions
    return results


def _default_base() -> Path:
    from mobile_crawler.config import get_app_data_dir

    return get_app_data_dir() / "output_data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", type=Path, help="output_data folder (default: the app data dir's output_data)")
    parser.add_argument("--dry-run", action="store_true", help="list what would change, touch nothing")
    args = parser.parse_args(argv)

    base = args.base or _default_base()
    if not base.is_dir():
        print(f"No output_data folder at {base}", file=sys.stderr)
        return 1

    results = migrate_all(base, dry_run=args.dry_run)
    skipped = 0
    for run, actions in results.items():
        print(f"{run.name}:")
        for action in actions:
            print(f"  {str(action).replace(str(run) + os.sep, '')}")
            skipped += action.kind == "skip"
    verb = "would change" if args.dry_run else "changed"
    print(f"\n{len(results)} run folder(s) {verb} under {base}; {skipped} file(s) skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
