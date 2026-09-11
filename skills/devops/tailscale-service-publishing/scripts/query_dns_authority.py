#!/usr/bin/env python3
"""Query A and AAAA records directly from an IPv4 DNS server.

Usage: query_dns_authority.py DNS_SERVER_IP HOSTNAME
Uses only the Python standard library; useful when dig/nslookup are absent.
"""

import random
import socket
import struct
import sys


def encode_name(name: str) -> bytes:
    return b"".join(bytes([len(label)]) + label.encode() for label in name.rstrip(".").split(".")) + b"\0"


def decode_name(message: bytes, offset: int):
    labels = []
    end = None
    while True:
        length = message[offset]
        if length & 0xC0 == 0xC0:
            if end is None:
                end = offset + 2
            offset = ((length & 0x3F) << 8) | message[offset + 1]
            continue
        offset += 1
        if length == 0:
            return ".".join(labels) + ".", (end or offset)
        labels.append(message[offset : offset + length].decode(errors="replace"))
        offset += length


def query(server: str, hostname: str, qtype: int):
    request_id = random.randrange(65536)
    packet = struct.pack("!HHHHHH", request_id, 0x0100, 1, 0, 0, 0)
    packet += encode_name(hostname) + struct.pack("!HH", qtype, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(packet, (server, 53))
    message, _ = sock.recvfrom(4096)
    response_id, flags, questions, answers, _, _ = struct.unpack("!HHHHHH", message[:12])
    if response_id != request_id:
        raise RuntimeError("DNS response ID mismatch")
    offset = 12
    for _ in range(questions):
        _, offset = decode_name(message, offset)
        offset += 4
    records = []
    for _ in range(answers):
        name, offset = decode_name(message, offset)
        record_type, _, ttl, length = struct.unpack("!HHIH", message[offset : offset + 10])
        offset += 10
        raw = message[offset : offset + length]
        offset += length
        if record_type == 1:
            value = socket.inet_ntop(socket.AF_INET, raw)
        elif record_type == 28:
            value = socket.inet_ntop(socket.AF_INET6, raw)
        else:
            continue
        records.append({"name": name, "type": record_type, "ttl": ttl, "value": value})
    return flags & 15, records


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: query_dns_authority.py DNS_SERVER_IP HOSTNAME")
    for qtype, label in ((1, "A"), (28, "AAAA")):
        rcode, records = query(sys.argv[1], sys.argv[2], qtype)
        print(f"{label} rcode={rcode} records={records}")


if __name__ == "__main__":
    main()
