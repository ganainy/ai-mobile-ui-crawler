"""Tests for running several packages one after another, each as its own Run."""

from mobile_crawler.cli.crawl_batch import run_crawl_batch


class FakeCrawler:
    """Records calls; each package's outcome, install state and failures are configurable."""

    def __init__(self, outcomes=None, missing=(), device_down_from=None, raise_on_run=None, interrupt_on=None):
        self.outcomes = outcomes or {}
        self.missing = set(missing)
        self.device_down_from = device_down_from  # index of the first device_ready() call that fails
        self.raise_on_run = raise_on_run or {}
        self.interrupt_on = interrupt_on
        self.calls = []
        self._next_run_id = 100

    def device_ready(self):
        checks = len([c for c in self.calls if c[0] == "device_ready"])
        ready = self.device_down_from is None or checks < self.device_down_from
        self.calls.append(("device_ready", ready))
        return ready

    def is_installed(self, package):
        self.calls.append(("is_installed", package))
        return package not in self.missing

    def force_stop(self, package):
        self.calls.append(("force_stop", package))

    def start_run(self, package):
        self._next_run_id += 1
        self.calls.append(("start_run", package, self._next_run_id))
        return self._next_run_id

    def run(self, run_id, package):
        self.calls.append(("run", run_id, package))
        if package == self.interrupt_on:
            raise KeyboardInterrupt
        if package in self.raise_on_run:
            raise self.raise_on_run[package]

    def outcome(self, run_id):
        package = next(c[2] for c in self.calls if c[0] == "run" and c[1] == run_id)
        return self.outcomes.get(package, ("COMPLETED", "duration_limit"))

    def mark_user_stopped(self, run_id):
        self.calls.append(("mark_user_stopped", run_id))
        package = next(c[2] for c in self.calls if c[0] == "run" and c[1] == run_id)
        self.outcomes.setdefault(package, ("STOPPED", "user_stop"))


def _batch(packages, crawler):
    return run_crawl_batch(packages, crawler)


def _names(calls, kind):
    return [c for c in calls if c[0] == kind]


def test_each_package_gets_its_own_run_in_list_order():
    crawler = FakeCrawler()

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert [c[1] for c in _names(crawler.calls, "start_run")] == ["com.a.app", "com.b.app"]
    assert [(e.package, e.run_id, e.status) for e in result.entries] == [
        ("com.a.app", 101, "COMPLETED"),
        ("com.b.app", 102, "COMPLETED"),
    ]
    assert result.exit_code == 0


def test_stop_reason_comes_from_the_finished_run():
    crawler = FakeCrawler(outcomes={"com.a.app": ("ERROR", "error: boom")})

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert (result.entries[0].status, result.entries[0].stop_reason) == ("ERROR", "error: boom")
    assert result.entries[1].status == "COMPLETED"
    assert result.exit_code == 1


def test_previous_app_is_force_stopped_before_the_next_one_starts():
    crawler = FakeCrawler()

    _batch(["com.a.app", "com.b.app"], crawler)

    order = [c[:2] for c in crawler.calls if c[0] in ("force_stop", "start_run")]
    assert order == [("start_run", "com.a.app"), ("force_stop", "com.a.app"), ("start_run", "com.b.app")]


def test_missing_package_is_skipped_and_the_batch_continues():
    crawler = FakeCrawler(missing={"com.a.app"})

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert (result.entries[0].status, result.entries[0].run_id) == ("SKIPPED", None)
    assert result.entries[0].stop_reason == "not installed"
    assert result.entries[1].status == "COMPLETED"
    assert [c[1] for c in _names(crawler.calls, "start_run")] == ["com.b.app"]
    assert _names(crawler.calls, "force_stop") == []
    assert result.exit_code == 1


def test_a_run_that_raises_is_an_error_and_the_batch_continues():
    crawler = FakeCrawler(raise_on_run={"com.a.app": RuntimeError("adb exploded")})

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert result.entries[0].status == "ERROR"
    assert "adb exploded" in result.entries[0].stop_reason
    assert result.entries[1].status == "COMPLETED"


def test_unreachable_device_stops_the_batch_and_leaves_the_rest_not_run():
    crawler = FakeCrawler(device_down_from=1)

    result = _batch(["com.a.app", "com.b.app", "com.c.app"], crawler)

    assert [e.status for e in result.entries] == ["COMPLETED", "NOT_RUN", "NOT_RUN"]
    assert result.aborted_reason == "device_unreachable"
    assert [c[1] for c in _names(crawler.calls, "start_run")] == ["com.a.app"]
    assert result.exit_code == 1


def test_ctrl_c_marks_the_current_run_stopped_and_ends_the_batch():
    crawler = FakeCrawler(interrupt_on="com.a.app")

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert ("mark_user_stopped", 101) in crawler.calls
    assert [(e.status, e.stop_reason) for e in result.entries] == [("STOPPED", "user_stop"), ("NOT_RUN", None)]
    assert result.aborted_reason == "user_stop"
    assert result.exit_code == 130


def test_summary_lists_every_package():
    crawler = FakeCrawler(missing={"com.b.app"})

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert result.to_dict() == {
        "aborted_reason": None,
        "runs": [
            {"package": "com.a.app", "run_id": 101, "status": "COMPLETED", "stop_reason": "duration_limit"},
            {"package": "com.b.app", "run_id": None, "status": "SKIPPED", "stop_reason": "not installed"},
        ],
    }


def test_ctrl_c_after_the_run_finished_keeps_its_recorded_outcome():
    # mark_user_stopped leaves a finished run alone, so the batch reports what the run recorded.
    crawler = FakeCrawler(interrupt_on="com.a.app", outcomes={"com.a.app": ("COMPLETED", "duration_limit")})

    result = _batch(["com.a.app", "com.b.app"], crawler)

    assert (result.entries[0].status, result.entries[0].stop_reason) == ("COMPLETED", "duration_limit")
    assert result.aborted_reason == "user_stop"
