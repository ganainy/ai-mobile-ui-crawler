"""Tests for TLS ClientHello SNI extraction from pcap files."""

import socket
import struct

import dpkt
import pytest

from mobile_crawler.infrastructure.sni_extractor import (
    extract_sni_records,
    parse_sni,
    reassemble,
    write_sni_report,
)


def client_hello_bytes(hostname: str) -> bytes:
    """Build a minimal (unencrypted-framing) TLS ClientHello record carrying `hostname` as SNI."""
    name = hostname.encode("ascii")
    server_name_entry = b"\x00" + struct.pack(">H", len(name)) + name  # name_type=host_name
    server_name_list = struct.pack(">H", len(server_name_entry)) + server_name_entry
    sni_extension = struct.pack(">HH", 0x0000, len(server_name_list)) + server_name_list

    extensions = sni_extension
    session_id = b""
    cipher_suites = struct.pack(">H", 0x1301)  # one cipher suite
    compression_methods = b"\x00"

    body = (
        b"\x03\x03"  # client_version
        + b"\x00" * 32  # random
        + bytes([len(session_id)])
        + session_id
        + struct.pack(">H", len(cipher_suites))
        + cipher_suites
        + bytes([len(compression_methods)])
        + compression_methods
        + struct.pack(">H", len(extensions))
        + extensions
    )
    handshake = b"\x01" + struct.pack(">I", len(body))[1:] + body  # ClientHello, 3-byte length
    record = b"\x16\x03\x01" + struct.pack(">H", len(handshake)) + handshake
    return record


def write_pcap(path, packets: list[tuple[int, bytes]]) -> None:
    """packets: list of (seq, tcp_payload); each becomes one raw-IP (linktype 101) TCP segment."""
    with open(path, "wb") as f:
        writer = dpkt.pcap.Writer(f, linktype=101)
        for seq, payload in packets:
            tcp = dpkt.tcp.TCP(sport=54321, dport=443, seq=seq, ack=1, flags=0x18, data=payload)
            ip = dpkt.ip.IP(src=socket.inet_aton("10.0.0.1"), dst=socket.inet_aton("93.184.216.34"), p=6, data=tcp)
            writer.writepkt(bytes(ip))


class TestParseSni:
    def test_single_record_client_hello(self):
        assert parse_sni(client_hello_bytes("example.com")) == "example.com"

    def test_not_a_handshake_record(self):
        assert parse_sni(b"\x17\x03\x03\x00\x05hello") is None

    def test_truncated_before_name_bytes_returns_none(self):
        full = client_hello_bytes("example.com")
        assert parse_sni(full[: len(full) - 3]) is None


class TestReassemble:
    def test_concatenates_contiguous_segments_in_seq_order(self):
        segments = {100: b"AAA", 103: b"BBB", 106: b"CCC"}
        assert reassemble(segments) == b"AAABBBCCC"

    def test_stops_at_a_gap(self):
        segments = {100: b"AAA", 200: b"ZZZ"}
        assert reassemble(segments) == b"AAA"


class TestExtractSniRecords:
    def test_single_packet_client_hello(self, tmp_path):
        pcap_path = tmp_path / "single.pcap"
        write_pcap(pcap_path, [(1000, client_hello_bytes("single.example.com"))])

        records = extract_sni_records(str(pcap_path))

        assert [r[3] for r in records] == ["single.example.com"]

    def test_fragmented_client_hello_is_reassembled(self, tmp_path):
        pcap_path = tmp_path / "fragmented.pcap"
        full = client_hello_bytes("fragmented.example.com")
        split_at = len(full) - 5  # split mid-hostname, like the run-196 truncation
        write_pcap(pcap_path, [(1000, full[:split_at]), (1000 + split_at, full[split_at:])])

        records = extract_sni_records(str(pcap_path))

        assert [r[3] for r in records] == ["fragmented.example.com"]

    def test_no_tls_traffic_returns_empty(self, tmp_path):
        pcap_path = tmp_path / "empty.pcap"
        write_pcap(pcap_path, [(1000, b"GET / HTTP/1.1\r\n\r\n")])

        assert extract_sni_records(str(pcap_path)) == []


class TestWriteSniReport:
    def test_writes_report_next_to_pcap(self, tmp_path):
        pcap_path = tmp_path / "run.pcap"
        write_pcap(pcap_path, [(1000, client_hello_bytes("reported.example.com"))])

        report_path = write_sni_report(str(pcap_path))

        assert report_path == str(tmp_path / "run.sni.txt")
        content = (tmp_path / "run.sni.txt").read_text()
        assert "reported.example.com" in content
