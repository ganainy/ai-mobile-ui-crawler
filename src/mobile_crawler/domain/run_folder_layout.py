"""Where each file of a run folder lives.

Every report of a run sits under ``reports/``; raw artifacts (screenshots, PCAP,
videos, APKs) stay in their own folders at the run folder's root::

    run_<id>_<date>_<time>/
    ├── reports/
    │   ├── run_report.html
    │   ├── analysis/            # Analysis Bundle
    │   ├── mobsf/               # MobSF JSON/PDF
    │   ├── config_snapshot.json
    │   └── crawler_trace.jsonl
    ├── screenshots/  videos/  pcap/  apks/
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunFolderLayout:
    """Paths inside one run folder. Pure: never touches the disk except the find_* lookups."""

    root: Path  # str accepted, converted in __post_init__

    CREATED_SUBFOLDERS = ("screenshots", "reports", "pcap", "videos", "apks")

    def __post_init__(self):
        object.__setattr__(self, "root", Path(self.root))

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def run_report_html(self) -> Path:
        return self.reports_dir / "run_report.html"

    @property
    def analysis_dir(self) -> Path:
        return self.reports_dir / "analysis"

    @property
    def mobsf_dir(self) -> Path:
        return self.reports_dir / "mobsf"

    @property
    def config_snapshot(self) -> Path:
        return self.reports_dir / "config_snapshot.json"

    @property
    def crawler_trace(self) -> Path:
        return self.reports_dir / "crawler_trace.jsonl"

    @property
    def screenshots_dir(self) -> Path:
        return self.root / "screenshots"

    @property
    def pcap_dir(self) -> Path:
        return self.root / "pcap"

    @property
    def videos_dir(self) -> Path:
        return self.root / "videos"

    @property
    def apks_dir(self) -> Path:
        return self.root / "apks"

    def find_mobsf_json_report(self) -> Path | None:
        """The newest ``<hash>_report.json`` MobSF saved for this run, or None."""
        return _newest(self.mobsf_dir, "*_report.json")

    def find_pcap(self) -> Path | None:
        """The newest traffic capture of this run, or None."""
        return _newest(self.pcap_dir, "*.pcap")


def _newest(folder: Path, pattern: str) -> Path | None:
    if not folder.is_dir():
        return None
    matches = [p for p in folder.glob(pattern) if p.is_file()]
    return max(matches, key=lambda p: p.stat().st_mtime) if matches else None
