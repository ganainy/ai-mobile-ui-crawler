"""Claude Code Stop hook: remind Claude to keep the vault up to date.

Blocks the stop once (exit 2) when
- src/ has uncommitted changes but docs/STATE.md does not, or
- a session note that debugs a run (mentions "run 123") changed but docs/findings/ did not.
stop_hook_active guards against loops.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}
if payload.get("stop_hook_active"):
    sys.exit(0)
out = subprocess.run(["git", "status", "--porcelain", "-uall"], capture_output=True, text=True).stdout.splitlines()
paths = [line[3:].strip().strip('"') for line in out]
code = any(p.startswith("src/") for p in paths)
state = any(p.endswith("docs/STATE.md") for p in paths)
if code and not state:
    print(
        "src/ changed but docs/STATE.md was not updated. Update docs/STATE.md and add a "
        "docs/sessions/ entry (see CLAUDE.md), then finish.",
        file=sys.stderr,
    )
    sys.exit(2)


def _debugs_a_run(path: str) -> bool:
    try:
        return bool(re.search(r"\brun \d{2,}\b", Path(path).read_text(encoding="utf-8"), re.IGNORECASE))
    except OSError:
        return False


sessions = [p for p in paths if p.startswith("docs/sessions/") and p.endswith(".md")]
findings = any(p.startswith("docs/findings/") for p in paths)
if not findings and any(_debugs_a_run(p) for p in sessions):
    print(
        "This session's note debugs a run but docs/findings/ was not touched. If the run showed how an app, "
        "device or tool behaves (see docs/findings/_index.md), add a finding note and an index row for the "
        "Masterarbeit; if it showed nothing new, say so and finish.",
        file=sys.stderr,
    )
    sys.exit(2)
