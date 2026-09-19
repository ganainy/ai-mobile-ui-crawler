"""Claude Code Stop hook: remind Claude to update docs/STATE.md after code changes.

Blocks the stop once (exit 2) when src/ has uncommitted changes but docs/STATE.md
does not. stop_hook_active guards against loops.
"""

import json
import subprocess
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}
if payload.get("stop_hook_active"):
    sys.exit(0)
out = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
paths = [line[3:] for line in out]
code = any(p.startswith("src/") for p in paths)
state = any(p.endswith("docs/STATE.md") for p in paths)
if code and not state:
    print(
        "src/ changed but docs/STATE.md was not updated. Update docs/STATE.md and add a "
        "docs/sessions/ entry (see CLAUDE.md), then finish.",
        file=sys.stderr,
    )
    sys.exit(2)
