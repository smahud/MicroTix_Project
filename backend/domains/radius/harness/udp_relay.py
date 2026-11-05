#!/usr/bin/env python3
"""Relay UDP dengan alamat sumber tertentu — harness RADIUS (dev/lab).

radclient/radtest tidak punya opsi bind alamat sumber, padahal resolusi
tenant facade RADIUS MicroTix memakai %{Packet-Src-IP-Address} (RADIUS.md
§4). Relay ini meneruskan paket UDP dari klien lokal ke daemon FreeRADIUS
melalui soket yang di-bind ke alamat sumber tertentu (mis. 127.0.0.2),
sehingga daemon (dan facade) melihat NAS yang benar tanpa hak root.

Pemetaan satu-arah per alamat klien; permintaan sekuensial radclient aman
(retransmisi memakai soket/sumber yang sama per klien).
"""
from __future__ import annotations

import argparse
import select
import socket
import sys
import time

IDLE_CLEANUP_S = 60.0


def parse_addr(value: str) -> tuple[str, int]:
    host, _, port = value.rpartition(":")
    if not host or not port.isdigit():
        raise SystemExit(f"alamat tidak valid: {value!r} (harus host:port)")
    return host, int(port)


def main() -> int:
    ap = argparse.ArgumentParser(description="Relay UDP dengan source IP tetap")
    ap.add_argument("--listen", required=True, help="alamat dengar radclient, mis. 127.0.0.1:28120")
    ap.add_argument("--source", required=True, help="alamat sumber ke arah daemon, mis. 127.0.0.2")
    ap.add_argument("--target", required=True, help="alamat daemon, mis. 127.0.0.1:18120")
    args = ap.parse_args()

    listen_addr = parse_addr(args.listen)
    source_ip = args.source
    target = parse_addr(args.target)

    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(listen_addr)

    # client_addr -> (socket bound source, last_used)
    flows: dict[tuple, tuple[socket.socket, float]] = {}

    def flow_for(client_addr):
        entry = flows.get(client_addr)
        if entry is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((source_ip, 0))
            entry = (sock, time.monotonic())
            flows[client_addr] = entry
        return entry

    print(f"relay {listen_addr[0]}:{listen_addr[1]} -> {target[0]}:{target[1]} (source {source_ip})", flush=True)
    try:
        while True:
            now = time.monotonic()
            socks = [listener] + [s for s, _ in flows.values()]
            readable, _, _ = select.select(socks, [], [], 5.0)
            for sock in readable:
                data, addr = sock.recvfrom(65535)
                if sock is listener:
                    out, _ = flow_for(addr)
                    out.sendto(data, target)
                    flows[addr] = (out, now)
                else:
                    for client, (s, _) in list(flows.items()):
                        if s is sock:
                            listener.sendto(data, client)
                            flows[client] = (s, now)
                            break
            # Bersihkan aliran menganggur (fd tidak bocor pada harness panjang).
            for client, (s, used) in list(flows.items()):
                if now - used > IDLE_CLEANUP_S:
                    s.close()
                    del flows[client]
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
