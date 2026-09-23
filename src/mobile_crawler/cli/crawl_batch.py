"""Runs `crawl` over several packages one after another, each package as its own Run.

A batch is a CLI convenience, not a domain concept: nothing about it is stored. Device and
database access sit behind `BatchCrawler`, so the ordering and failure rules here stay testable.
"""

from dataclasses import asdict, dataclass, field
from typing import Protocol

EXIT_INTERRUPTED = 130


class BatchCrawler(Protocol):
    def device_ready(self) -> bool: ...

    def is_installed(self, package: str) -> bool: ...

    def force_stop(self, package: str) -> None: ...

    def start_run(self, package: str) -> int: ...

    def run(self, run_id: int, package: str) -> None: ...

    def outcome(self, run_id: int) -> tuple[str, str | None]: ...

    def mark_user_stopped(self, run_id: int) -> None:
        """Record a still-running Run as stopped by the user; leave a finished one as it is."""


@dataclass
class BatchEntry:
    package: str
    run_id: int | None = None
    # COMPLETED / STOPPED / ERROR from the finished Run, or SKIPPED / NOT_RUN when no crawl happened.
    status: str = "NOT_RUN"
    stop_reason: str | None = None


@dataclass
class BatchResult:
    entries: list[BatchEntry] = field(default_factory=list)
    aborted_reason: str | None = None  # "device_unreachable" or "user_stop"

    @property
    def exit_code(self) -> int:
        if self.aborted_reason == "user_stop":
            return EXIT_INTERRUPTED
        return 0 if all(e.status == "COMPLETED" for e in self.entries) else 1

    def to_dict(self) -> dict:
        return {"aborted_reason": self.aborted_reason, "runs": [asdict(e) for e in self.entries]}


def run_crawl_batch(packages: list[str], crawler: BatchCrawler) -> BatchResult:
    """Crawl each package in order. A failed app is recorded and skipped; a lost device or Ctrl+C ends the batch."""
    result = BatchResult(entries=[BatchEntry(package) for package in packages])
    previous: str | None = None
    for entry in result.entries:
        try:
            if not _device_ready(crawler):
                result.aborted_reason = "device_unreachable"
                break
            if previous is not None:
                _force_stop(crawler, previous)
                previous = None
            if not crawler.is_installed(entry.package):
                entry.status, entry.stop_reason = "SKIPPED", "not installed"
                continue
            entry.run_id = crawler.start_run(entry.package)
            previous = entry.package
            crawler.run(entry.run_id, entry.package)
            entry.status, entry.stop_reason = crawler.outcome(entry.run_id)
        except KeyboardInterrupt:
            if entry.run_id is not None:
                crawler.mark_user_stopped(entry.run_id)
                entry.status, entry.stop_reason = crawler.outcome(entry.run_id)
            result.aborted_reason = "user_stop"
            break
        except Exception as e:
            entry.status, entry.stop_reason = "ERROR", f"error: {e}"
    return result


def _device_ready(crawler: BatchCrawler) -> bool:
    try:
        return crawler.device_ready()
    except Exception:
        return False


def _force_stop(crawler: BatchCrawler, package: str) -> None:
    # Only there to give the next app a clean start; a failure must not cost it its run.
    try:
        crawler.force_stop(package)
    except Exception:
        pass
