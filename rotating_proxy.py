# rotating_proxy.py
"""
A lightweight local rotating proxy server.

Chrome is pointed at 127.0.0.1:LOCAL_PORT via --proxy-server.
Each incoming HTTPS CONNECT tunnel is forwarded through the next upstream
proxy in the round-robin pool. When the pool runs low a background thread
refetches more proxies automatically. When the pool is empty the connection
falls through to a direct connection so Chrome never goes dark.
"""

import base64
import select
import socket
import logging
import threading
import socketserver

logger = logging.getLogger(__name__)

LOCAL_PORT = 18888
_REPLENISH_THRESHOLD = 3   # start fetching when live count drops to this
_REPLENISH_TARGET    = 10  # how many new working proxies to aim for


def _tunnel(client: socket.socket, upstream: socket.socket) -> None:
    """Relay bytes bidirectionally until either side closes or times out."""
    client.setblocking(False)
    upstream.setblocking(False)
    try:
        while True:
            readable, _, _ = select.select([client, upstream], [], [], 30)
            if not readable:
                break
            for sock in readable:
                other = upstream if sock is client else client
                try:
                    data = sock.recv(65536)
                    if not data:
                        return
                    other.sendall(data)
                except OSError:
                    return
    finally:
        for s in (client, upstream):
            try:
                s.close()
            except OSError:
                pass


class _TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class RotatingProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server: "RotatingProxyServer" = self.server.proxy_server  # type: ignore[attr-defined]

        # Read the full HTTP header from Chrome
        raw = b""
        try:
            while b"\r\n\r\n" not in raw:
                chunk = self.request.recv(4096)
                if not chunk:
                    return
                raw += chunk
        except OSError:
            return

        first_line = raw.split(b"\r\n")[0].decode(errors="replace")
        parts = first_line.split()
        if len(parts) < 2:
            return
        method = parts[0]

        # Try each live proxy in round-robin order
        n_to_try = max(len(server.proxies), 1)
        for _ in range(n_to_try):
            proxy = server.next_proxy()
            if proxy is None:
                break  # pool empty — fall through to direct connection

            host, port_str = proxy.rsplit(":", 1)
            try:
                upstream = socket.create_connection((host, int(port_str)), timeout=10)
            except OSError:
                server.mark_dead(proxy)
                continue

            try:
                # For authenticated upstreams (e.g. DataImpulse), inject
                # Proxy-Authorization into the CONNECT request before forwarding.
                outgoing = raw
                if method == "CONNECT" and server._auth:
                    b64 = base64.b64encode(server._auth.encode()).decode()
                    auth_line = f"Proxy-Authorization: Basic {b64}\r\n".encode()
                    # raw ends with \r\n\r\n — insert auth before the blank line
                    outgoing = raw[:-2] + auth_line + b"\r\n"
                upstream.sendall(outgoing)

                if method == "CONNECT":
                    resp = b""
                    while b"\r\n\r\n" not in resp:
                        chunk = upstream.recv(4096)
                        if not chunk:
                            break
                        resp += chunk

                    if b"200" not in resp.split(b"\r\n")[0]:
                        server.mark_dead(proxy)
                        upstream.close()
                        continue

                    self.request.sendall(resp)
                    _tunnel(self.request, upstream)
                else:
                    while True:
                        chunk = upstream.recv(8192)
                        if not chunk:
                            break
                        self.request.sendall(chunk)
                    upstream.close()

                return  # success
            except OSError:
                server.mark_dead(proxy)
                try:
                    upstream.close()
                except OSError:
                    pass

        # ── Fallback: direct connection (no upstream proxy) ──────────────────
        # Keeps Chrome working even when the entire pool is dead.
        logger.debug("No live proxies — falling back to direct connection.")
        self._direct(method, parts[1], raw)

    def _direct(self, method: str, target: str, raw: bytes) -> None:
        """Connect directly to the target without an upstream proxy."""
        try:
            if method == "CONNECT":
                # target is "host:port"
                host, port_str = target.rsplit(":", 1)
                upstream = socket.create_connection((host, int(port_str)), timeout=15)
                self.request.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                _tunnel(self.request, upstream)
            else:
                # Plain HTTP — extract host from Host header
                for line in raw.split(b"\r\n")[1:]:
                    if line.lower().startswith(b"host:"):
                        host_val = line.split(b":", 1)[1].strip().decode()
                        host = host_val.split(":")[0]
                        port = int(host_val.split(":")[1]) if ":" in host_val else 80
                        upstream = socket.create_connection((host, port), timeout=15)
                        upstream.sendall(raw)
                        while True:
                            chunk = upstream.recv(8192)
                            if not chunk:
                                break
                            self.request.sendall(chunk)
                        upstream.close()
                        break
        except OSError:
            pass


class RotatingProxyServer:
    def __init__(self, proxies: list[str], port: int = LOCAL_PORT, auth: str | None = None) -> None:
        """
        proxies : list of "host:port" upstream proxy strings.
        auth    : optional "username:password" for authenticated upstreams
                  (e.g. DataImpulse). The credential is injected as a
                  Proxy-Authorization header on every CONNECT request.
        """
        self._all: list[str] = list(proxies)
        self._dead: set[str] = set()
        self._idx: int = 0
        self._lock = threading.Lock()
        self._replenishing: bool = False
        self._auth: str | None = auth
        self.port = port
        self._server: _TCPServer | None = None

    @property
    def proxies(self) -> list[str]:
        with self._lock:
            return [p for p in self._all if p not in self._dead]

    def next_proxy(self) -> str | None:
        with self._lock:
            live = [p for p in self._all if p not in self._dead]
            if not live:
                return None
            proxy = live[self._idx % len(live)]
            self._idx += 1
            return proxy

    def add_proxies(self, new_proxies: list[str]) -> None:
        with self._lock:
            added = 0
            for p in new_proxies:
                if p not in self._all:
                    self._all.append(p)
                    added += 1
                elif p in self._dead:
                    self._dead.discard(p)  # revive if previously dead
                    added += 1
        if added:
            logger.info(f"Pool replenished +{added} proxies ({len(self.proxies)} live).")

    def mark_dead(self, proxy: str) -> None:
        with self._lock:
            if proxy in self._dead:
                return
            self._dead.add(proxy)
            remaining = len(self._all) - len(self._dead)
        logger.warning(f"Proxy {proxy} marked dead — {remaining} remaining.")
        self._maybe_replenish()

    def _maybe_replenish(self) -> None:
        """Kick off a background refetch if the live pool is running low."""
        with self._lock:
            live = len(self._all) - len(self._dead)
            if live > _REPLENISH_THRESHOLD or self._replenishing:
                return
            self._replenishing = True

        def _refill() -> None:
            from proxy import get_working_proxies  # local import avoids circular dep
            logger.info(f"Pool low — fetching {_REPLENISH_TARGET} fresh proxies in background...")
            fresh = get_working_proxies(n=_REPLENISH_TARGET, limit=150)
            if fresh:
                self.add_proxies(fresh)
            else:
                logger.warning("Background replenishment found no working proxies.")
            with self._lock:
                self._replenishing = False

        threading.Thread(target=_refill, daemon=True).start()

    def start(self) -> None:
        server = _TCPServer(("127.0.0.1", self.port), RotatingProxyHandler)
        server.proxy_server = self  # type: ignore[attr-defined]
        self._server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        logger.info(
            f"Rotating proxy on 127.0.0.1:{self.port} "
            f"with {len(self._all)} upstream(s)."
        )

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
