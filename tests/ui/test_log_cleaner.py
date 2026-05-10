"""Tests for UI log cleaning."""

from mobile_crawler.ui.log_cleaner import LogCleaner


def test_clean_strips_ansi_codes():
    cleaner = LogCleaner()

    assert cleaner.clean("test", "\x1b[36mStep 1 started\x1b[0m") == "Step 1 started"


def test_clean_suppresses_stdout_duplicate_within_window():
    cleaner = LogCleaner()

    assert cleaner.clean("droidrun", "Step 1 started") == "Step 1 started"
    assert cleaner.clean("stdout", "[stdout] Step 1 started") is None


def test_clean_strips_stdout_prefix_when_not_duplicate():
    cleaner = LogCleaner()

    assert cleaner.clean("stdout", "[stdout] Manager response: ok") == "Manager response: ok"


def test_clean_suppresses_known_noise():
    cleaner = LogCleaner()

    assert cleaner.clean("PIL.PngImagePlugin", "PIL.PngImagePlugin: STREAM b'IHDR' 16 13") is None
    assert cleaner.clean("asyncio", "asyncio: Using proactor: IocpProactor") is None


def test_clean_deduplicates_logger_prefix_variants():
    cleaner = LogCleaner()

    assert cleaner.clean("droidrun", "droidrun: Executing tap") == "droidrun: Executing tap"
    assert cleaner.clean("stdout", "[stdout] Executing tap") is None
