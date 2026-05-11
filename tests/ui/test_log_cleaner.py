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


def test_clean_formats_omniparser_element_payload_for_readability():
    cleaner = LogCleaner()

    cleaned = cleaner.clean(
        "mobile_crawler.domain.omni_parser_client",
        "First valid element: {'type': 'text', 'bbox': [0.1, 0.2, 0.3, 0.4], 'interactivity': False, 'content': 'Hello'}",
    )

    assert cleaned is not None
    assert cleaned.startswith("First valid element:")
    assert "  type: text" in cleaned
    assert "  interactivity: False" in cleaned
    assert "  content: Hello" in cleaned
    assert "  bbox: [0.1, 0.2, 0.3, 0.4]" in cleaned


def test_clean_unescapes_omniparser_escaped_newlines():
    cleaner = LogCleaner()

    cleaned = cleaner.clean(
        "mobile_crawler.domain.omni_parser_client",
        r"icon 1: {'type': 'text', 'bbox': [0.1, 0.2, 0.3, 0.4], 'interactivity': False, 'content': 'Schon; Sie zu sehenl'}\nicon 2: {'type': 'text', 'bbox': [0.0, 0.0, 1.0, 1.0], 'interactivity': False, 'content': 'Weiter'}",
    )

    assert cleaned is not None
    assert "\nicon 2:" in cleaned
