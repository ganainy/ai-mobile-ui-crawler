"""Tests for the Live Feed scrcpy stream (no device needed)."""

from fractions import Fraction

import av
import numpy as np
import pytest

from mobile_crawler.domain import scrcpy_stream
from mobile_crawler.domain.scrcpy_stream import (
    SERVER_JAR,
    SERVER_VERSION,
    H264Decoder,
    ScrcpyStream,
    ScrcpyStreamError,
    build_server_args,
    parse_wm_size,
)


def test_vendored_jar_matches_pinned_version():
    assert SERVER_JAR.is_file()
    assert SERVER_JAR.name == f"scrcpy-server-v{SERVER_VERSION}.jar"


def test_server_args_are_video_only_raw_forward_tunnel():
    args = build_server_args(0xABC, 720, 15)
    assert args[0] == SERVER_VERSION  # server refuses to start on a mismatch
    assert "scid=00000abc" in args
    for expected in ("audio=false", "control=false", "raw_stream=true", "tunnel_forward=true"):
        assert expected in args
    assert "max_size=720" in args and "max_fps=15" in args


def test_parse_wm_size_physical_and_override():
    assert parse_wm_size("Physical size: 1080x2400\n") == (1080, 2400)
    both = "Physical size: 1080x2400\nOverride size: 720x1600\n"
    assert parse_wm_size(both) == (720, 1600)
    assert parse_wm_size("garbage") is None


def _encode_h264(frames: int = 5, size: tuple[int, int] = (64, 96)) -> bytes:
    import io

    buf = io.BytesIO()
    with av.open(buf, mode="w", format="h264") as container:
        stream = container.add_stream("libx264", rate=Fraction(15))
        stream.width, stream.height = size
        stream.pix_fmt = "yuv420p"
        for i in range(frames):
            img = np.full((size[1], size[0], 3), i * 40, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(img, format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return buf.getvalue()


def test_decoder_returns_latest_rgb_frame():
    try:
        data = _encode_h264()
    except Exception as exc:  # libx264 missing in this PyAV build
        pytest.skip(f"no h264 encoder available: {exc}")
    frame = H264Decoder().feed(data)
    assert frame is not None
    assert frame.shape == (96, 64, 3)
    assert frame.flags["C_CONTIGUOUS"]  # QImage needs a contiguous buffer


def test_decoder_ignores_garbage():
    assert H264Decoder().feed(b"\x00\x01not h264") is None


def test_start_fails_cleanly_when_jar_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(scrcpy_stream, "SERVER_JAR", tmp_path / "nope.jar")
    with pytest.raises(ScrcpyStreamError, match="jar missing"):
        ScrcpyStream("adb", "serial").start()


def test_adb_commands_target_the_selected_serial(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "Physical size: 1080x2400"
        stderr = ""

    monkeypatch.setattr(scrcpy_stream.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or Result())
    stream = ScrcpyStream("my-adb", "adb-XYZ._adb-tls-connect._tcp")
    assert stream.device_size() == (1080, 2400)
    assert calls[0][:3] == ["my-adb", "-s", "adb-XYZ._adb-tls-connect._tcp"]
