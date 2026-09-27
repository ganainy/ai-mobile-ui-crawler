"""Extract TLS ClientHello SNI hostnames from a pcap file.

Reassembles fragmented ClientHellos at the TCP layer, since the SNI extension
can be split across segments (see docs/sessions/2026-09-27-emulator-tls-ca-naming.md
for how this surfaced: a truncated hostname from a single-packet-only parse).
"""

import socket
import struct
from collections import defaultdict
from pathlib import Path

import dpkt

MAX_REASSEMBLED = 65536  # ClientHellos don't realistically exceed this; caps memory per flow
LINKTYPE_RAW = 101  # Linux/Android VPN-capture raw IP; dpkt's DLT_RAW (12) is the BSD variant


def parse_sni(payload: bytes) -> str | None:
    if len(payload) < 6 or payload[0] != 0x16:  # TLS record type: handshake
        return None
    pos = 5  # skip record header (type, version, length)
    if pos >= len(payload) or payload[pos] != 0x01:  # handshake type: ClientHello
        return None
    pos += 4  # skip handshake type + length
    pos += 2 + 32  # client_version + random
    if pos >= len(payload):
        return None
    session_id_len = payload[pos]
    pos += 1 + session_id_len
    if pos + 2 > len(payload):
        return None
    cipher_suites_len = struct.unpack(">H", payload[pos : pos + 2])[0]
    pos += 2 + cipher_suites_len
    if pos >= len(payload):
        return None
    compression_len = payload[pos]
    pos += 1 + compression_len
    if pos + 2 > len(payload):
        return None
    extensions_len = struct.unpack(">H", payload[pos : pos + 2])[0]
    pos += 2
    end = pos + extensions_len
    while pos + 4 <= end and pos + 4 <= len(payload):
        ext_type, ext_len = struct.unpack(">HH", payload[pos : pos + 4])
        pos += 4
        if ext_type == 0x0000:  # server_name
            name_len = struct.unpack(">H", payload[pos + 3 : pos + 5])[0]
            sni_pos = pos + 5
            if sni_pos + name_len > len(payload):
                return None  # ClientHello not fully reassembled yet
            return payload[sni_pos : sni_pos + name_len].decode("ascii", errors="replace")
        pos += ext_len
    return None


def ip_packet(buf: bytes, linktype: int) -> dpkt.ip.IP | None:
    if linktype == dpkt.pcap.DLT_EN10MB:
        eth = dpkt.ethernet.Ethernet(buf)
        return eth.data if isinstance(eth.data, dpkt.ip.IP) else None
    if linktype in (dpkt.pcap.DLT_RAW, LINKTYPE_RAW):
        return dpkt.ip.IP(buf)
    if linktype == dpkt.pcap.DLT_LINUX_SLL:
        cooked = dpkt.sll.SLL(buf)
        return cooked.data if isinstance(cooked.data, dpkt.ip.IP) else None
    return None


def reassemble(segments: dict[int, bytes]) -> bytes:
    """Concatenate TCP segments in sequence order, starting from the lowest seq seen.

    Only contiguous runs count; a gap (missing/out-of-order segment not yet seen)
    stops reassembly at that point, same as a real TCP receive buffer would.
    """
    start = min(segments)
    buf = bytearray()
    seq = start
    while seq in segments:
        chunk = segments[seq]
        buf.extend(chunk)
        seq += len(chunk)
    return bytes(buf)


def extract_sni_records(pcap_path: str) -> list[tuple[float, str, str, str]]:
    """Return (timestamp, src_ip, dst_ip, sni_hostname) for every ClientHello found."""
    records: list[tuple[float, str, str, str]] = []

    # keyed by (src, sport, dst, dport): only tracks flows whose first data segment
    # looked like a TLS handshake, so a fragmented ClientHello can be reassembled
    # before parse_sni sees it.
    flows: dict[tuple[str, int, str, int], dict[int, bytes]] = defaultdict(dict)
    done: set[tuple[str, int, str, int]] = set()

    with open(pcap_path, "rb") as f:
        reader = dpkt.pcap.Reader(f)
        linktype = reader.datalink()
        for ts, buf in reader:
            try:
                ip = ip_packet(buf, linktype)
            except (dpkt.dpkt.UnpackError, dpkt.dpkt.NeedData):
                continue
            if ip is None or not isinstance(ip.data, dpkt.tcp.TCP):
                continue
            tcp = ip.data
            if not tcp.data:
                continue

            src = socket.inet_ntoa(ip.src)
            dst = socket.inet_ntoa(ip.dst)
            flow_key = (src, tcp.sport, dst, tcp.dport)
            if flow_key in done:
                continue

            segments = flows.get(flow_key)
            if segments is None:
                if bytes(tcp.data[:1]) != b"\x16":  # not the start of a TLS handshake
                    continue
                segments = flows[flow_key]

            segments.setdefault(tcp.seq, bytes(tcp.data))
            payload = reassemble(segments)
            if len(payload) > MAX_REASSEMBLED:
                del flows[flow_key]  # give up: not a ClientHello we can parse
                continue

            sni = parse_sni(payload)
            if sni:
                records.append((ts, src, dst, sni))
                done.add(flow_key)
                del flows[flow_key]

    return records


def write_sni_report(pcap_path: str) -> str:
    """Extract SNI hostnames from a pcap and write them next to it as <name>.sni.txt.

    Returns the report's path. Raises on read/parse failure; callers should treat
    this as best-effort and not fail the run over it.
    """
    records = extract_sni_records(pcap_path)
    report_path = Path(pcap_path).with_suffix(".sni.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        for ts, src, dst, sni in records:
            f.write(f"{ts:.6f}  {src} -> {dst}  {sni}\n")
    return str(report_path)
