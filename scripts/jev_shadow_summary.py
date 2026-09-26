"""Summarize jev_shadow.jsonl files: is Jev good and fast enough to be worth a Jev-first Executor (issue #29)?

Usage (through the project venv)::

    .venv312/Scripts/python.exe scripts/jev_shadow_summary.py PATH [PATH ...]
    .venv312/Scripts/python.exe scripts/jev_shadow_summary.py PATH --db path/to/crawler.db

PATH is a ``jev_shadow.jsonl`` or a run folder holding ``reports/jev_shadow.jsonl``.
Prints agreement per Jev confidence bucket, coverage, latency percentiles and, when the run
folder is named ``run_<id>_...`` and the database has that run's phase timings, the Executor's
share of step time. Ends with the go / no-go checks from the issue.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BUCKETS = ((0.95, 1.01), (0.85, 0.95), (0.7, 0.85), (0.0, 0.7))
CONFIDENT = 0.85


def load(paths: list[Path]) -> list[dict]:
    lines = []
    for path in paths:
        file = path / "reports" / "jev_shadow.jsonl" if path.is_dir() else path
        for raw in file.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                lines.append(json.loads(raw))
    return lines


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


def _ratio(part: float, whole: float | None) -> float | None:
    return part / whole if whole else None


def summarize(lines: list[dict], step_time_ms: float | None = None) -> dict:
    """Numbers behind the go / no-go checks; ``step_time_ms`` is the total step time of the same runs."""
    comparable = [line for line in lines if line["agree"] is not None]
    confident = [line for line in comparable if (line["jev"]["confidence"] or 0) >= CONFIDENT]
    buckets = []
    for low, high in BUCKETS:
        inside = [line for line in comparable if low <= (line["jev"]["confidence"] or 0) < high]
        buckets.append(
            {
                "range": (low, min(high, 1.0)),
                "steps": len(inside),
                "agreed": sum(1 for line in inside if line["agree"]),
            }
        )
    jev_ms = [
        line["jev"]["latency_ms"]
        for line in lines
        if line["jev"]["latency_ms"] is not None and not line["jev"]["error"]
    ]
    executor_ms = [line["executor"]["latency_ms"] for line in lines if line["executor"]["latency_ms"] is not None]
    return {
        "steps": len(lines),
        "comparable": len(comparable),
        "errors": sum(1 for line in lines if line["jev"]["error"]),
        "agreement": _ratio(sum(1 for line in comparable if line["agree"]), len(comparable)),
        "buckets": buckets,
        "confident_agreement": _ratio(sum(1 for line in confident if line["agree"]), len(confident)),
        "confident_coverage": _ratio(len(confident), len(comparable)),
        "jev_ms": {p: percentile(jev_ms, p) for p in (50, 90, 99)},
        "executor_ms": {p: percentile(executor_ms, p) for p in (50, 90, 99)},
        "executor_share": _ratio(sum(executor_ms), step_time_ms),
    }


def total_step_time_ms(db_path: Path, run_id: int) -> float | None:
    """Sum of the run's phase durations (phases run one after another)."""
    try:
        conn = sqlite3.connect(db_path)
        try:
            (total,) = conn.execute(
                "SELECT SUM(duration_ms) FROM step_phase_transitions WHERE run_id = ?", (run_id,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return total


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f} ms"


def _mark(ok: bool | None) -> str:
    return "?" if ok is None else "x" if ok else " "


def format_summary(result: dict) -> str:
    jev, exe = result["jev_ms"], result["executor_ms"]
    out = [
        f"Executor steps logged: {result['steps']}  "
        f"(comparable: {result['comparable']}, Jev errors: {result['errors']})",
        f"Overall agreement: {_pct(result['agreement'])}",
        "Agreement by Jev confidence:",
    ]
    for bucket in result["buckets"]:
        low, high = bucket["range"]
        out.append(f"  {low:.2f}-{high:.2f}: {bucket['agreed']}/{bucket['steps']} agree")
    out += [
        f"Jev latency    p50/p90/p99: {_ms(jev[50])} / {_ms(jev[90])} / {_ms(jev[99])}",
        f"Executor LLM   p50/p90/p99: {_ms(exe[50])} / {_ms(exe[90])} / {_ms(exe[99])}",
        f"Executor share of step time: {_pct(result['executor_share'])}",
        "",
        "Go / no-go (all must hold):",
    ]
    checks = [
        (
            f"agreement at confidence >= {CONFIDENT} is >= 90%",
            None if result["confident_agreement"] is None else result["confident_agreement"] >= 0.9,
            _pct(result["confident_agreement"]),
        ),
        (
            "confident steps are >= 50% of steps",
            None if result["confident_coverage"] is None else result["confident_coverage"] >= 0.5,
            _pct(result["confident_coverage"]),
        ),
        ("Jev median latency < 500 ms", None if jev[50] is None else jev[50] < 500, _ms(jev[50])),
        (
            "Executor >= ~25% of step time",
            None if result["executor_share"] is None else result["executor_share"] >= 0.25,
            _pct(result["executor_share"]),
        ),
    ]
    out += [f"  [{_mark(ok)}] {label}: {shown}" for label, ok, shown in checks]
    return "\n".join(out)


def _run_id(path: Path) -> int | None:
    folder = path if path.is_dir() else path.parent.parent
    match = re.match(r"run_(\d+)_", folder.name)
    return int(match.group(1)) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--db", type=Path, default=None, help="crawler.db, for the Executor's share of step time")
    args = parser.parse_args(argv)

    lines = load(args.paths)
    if not lines:
        print("No Jev shadow lines found.", file=sys.stderr)
        return 1
    db = args.db
    if db is None:
        from mobile_crawler.config.paths import get_app_data_dir

        db = get_app_data_dir() / "crawler.db"
    step_time = None
    if db.exists():
        run_ids = [_run_id(path) for path in args.paths]
        totals = [total_step_time_ms(db, run_id) for run_id in run_ids if run_id is not None]
        if totals and len(totals) == len(run_ids) and all(total is not None for total in totals):
            step_time = sum(totals)
    print(format_summary(summarize(lines, step_time)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
