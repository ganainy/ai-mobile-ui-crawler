"""Print each TLS ClientHello's SNI hostname found in a pcap file.

Usage: .venv312/Scripts/python.exe scripts/extract_sni.py <path-to-pcap>
"""
import sys

from mobile_crawler.infrastructure.sni_extractor import extract_sni_records


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-pcap>", file=sys.stderr)
        raise SystemExit(1)

    for ts, src, dst, sni in extract_sni_records(sys.argv[1]):
        print(f"{ts:.6f}  {src} -> {dst}  {sni}")


if __name__ == "__main__":
    main()
