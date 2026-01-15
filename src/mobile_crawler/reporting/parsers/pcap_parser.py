import dpkt
import socket
from datetime import datetime
from typing import List
from ..contracts import PcapParser, NetworkRequest

class DpktPcapParser(PcapParser):
    MAX_REQUESTS = 1000

    def parse(self, pcap_path: str) -> List[NetworkRequest]:
        requests = []
        try:
            with open(pcap_path, 'rb') as f:
                pcap = dpkt.pcap.Reader(f)
                for ts, buf in pcap:
                    if len(requests) >= self.MAX_REQUESTS:
                        break
                    eth = dpkt.ethernet.Ethernet(buf)
                    if not isinstance(eth.data, dpkt.ip.IP):
                        continue
                    
                    ip = eth.data
                    if not isinstance(ip.data, dpkt.tcp.TCP):
                        continue
                    
                    tcp = ip.data
                    if tcp.dport == 80 or tcp.sport == 80 or tcp.dport == 443 or tcp.sport == 443:
                        # Attempt to parse HTTP
                        try:
                            if tcp.dport == 80 and len(tcp.data) > 0:
                                http = dpkt.http.Request(tcp.data)
                                host = http.headers.get('host', '')
                                url = f"http://{host}{http.uri}"
                                requests.append(NetworkRequest(
                                    timestamp=datetime.fromtimestamp(ts),
                                    method=http.method,
                                    url=url,
                                    host=host,
                                    protocol=f"HTTP/{http.version}"
                                ))
                            elif tcp.dport == 443:
                                # TLS parsing is complex with dpkt, for now just log as HTTPS
                                # This is a placeholder for real TLS SNI extraction if needed
                                requests.append(NetworkRequest(
                                    timestamp=datetime.fromtimestamp(ts),
                                    method="CONNECT",
                                    url="https://unknown",
                                    host="unknown",
                                    protocol="TLS"
                                ))
                        except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                            continue
        except FileNotFoundError:
            return []
        
        return requests
