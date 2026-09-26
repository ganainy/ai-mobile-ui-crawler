import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import jev_shadow_summary as summary  # noqa: E402


def line(agree, confidence, jev_ms=200.0, executor_ms=1000.0, error=None):
    return {
        "step": 1,
        "subgoal": "x",
        "jev": {"confidence": confidence, "latency_ms": jev_ms, "error": error},
        "executor": {"latency_ms": executor_ms},
        "agree": agree,
    }


def test_summarize_buckets_coverage_and_share():
    lines = [
        line(True, 0.97),
        line(True, 0.9),
        line(False, 0.88),
        line(False, 0.5),
        line(None, 0.9),  # typing step: excluded
    ]

    result = summary.summarize(lines, step_time_ms=8000.0)

    assert result["comparable"] == 4
    assert result["confident_coverage"] == 0.75
    assert abs(result["confident_agreement"] - 2 / 3) < 1e-9
    assert result["executor_share"] == 5000.0 / 8000.0
    assert result["jev_ms"][50] == 200.0
    assert [b["steps"] for b in result["buckets"]] == [1, 2, 0, 1]


def test_main_prints_go_no_go_for_a_sample_file(tmp_path, capsys):
    run = tmp_path / "run_7_2026-09-26_10-00-00"
    (run / "reports").mkdir(parents=True)
    rows = [line(True, 0.95) for _ in range(9)] + [line(False, 0.9)]
    (run / "reports" / "jev_shadow.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    code = summary.main([str(run), "--db", str(tmp_path / "missing.db")])

    out = capsys.readouterr().out
    assert code == 0
    assert "Executor steps logged: 10" in out
    assert "[x] agreement at confidence >= 0.85 is >= 90%: 90%" in out
    assert "[?] Executor >= ~25% of step time: n/a" in out
