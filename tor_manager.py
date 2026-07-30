"""
Tor multi-instance manager.

Launches ONE Tor process configured with N SocksPorts + N ControlPorts.
Each browser instance uses its own isolated Tor circuit, so IPs never bleed
across windows.

Calling new_circuit(i) sends SIGNAL NEWNYM to that instance's circuit,
giving the next request a different exit node (= different visible IP).
Tor enforces a 10-second cooldown between NEWNYM calls per circuit.

Requirements:
    pip install stem
    Tor Expert Bundle from https://www.torproject.org/download/tor/
    Set TOR_PATH in .env to the tor.exe binary path.
"""
import os
import time
import logging
import subprocess
import socket
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_BASE_SOCKS   = 9050   # instance i uses port 9050+i
_BASE_CONTROL = 9150   # instance i uses control port 9150+i
_DATA_DIR     = os.path.join(os.path.dirname(__file__), "tor-data")
_NEWNYM_COOLDOWN = 10  # seconds — Tor's enforced minimum between NEWNYM signals


class TorManager:
    def __init__(self, n_instances: int, tor_path: str, control_pass: str = "") -> None:
        self._n            = n_instances
        self._tor_path     = tor_path
        self._control_pass = control_pass
        self._proc: Optional[subprocess.Popen] = None
        self._controllers: list = []
        self._last_newnym: list[float] = [0.0] * n_instances
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def socks_addr(self, i: int) -> str:
        """Return the SOCKS5 proxy address string for instance i."""
        return f"socks5://127.0.0.1:{_BASE_SOCKS + i}"

    def start(self) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        torrc = os.path.join(_DATA_DIR, "torrc")
        self._write_torrc(torrc)

        logger.info(f"Starting Tor ({self._n} SocksPorts)…")
        self._proc = subprocess.Popen(
            [self._tor_path, "-f", torrc],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_control_port(timeout=90)
        self._connect_controllers()
        logger.info("Tor ready.")

    def new_circuit(self, i: int) -> None:
        """Request a new exit node for instance i (respects 10 s cooldown)."""
        now = time.time()
        with self._lock:
            elapsed = now - self._last_newnym[i]
            if elapsed < _NEWNYM_COOLDOWN:
                wait = _NEWNYM_COOLDOWN - elapsed
            else:
                wait = 0
            self._last_newnym[i] = now + wait  # reserve the slot

        if wait:
            time.sleep(wait)

        if i < len(self._controllers) and self._controllers[i] is not None:
            try:
                from stem import Signal
                self._controllers[i].signal(Signal.NEWNYM)
                logger.debug(f"[tor:{i}] new circuit requested")
            except Exception as e:
                logger.warning(f"[tor:{i}] NEWNYM failed: {e}")

    def stop(self) -> None:
        for ctrl in self._controllers:
            if ctrl is not None:
                try:
                    ctrl.close()
                except Exception:
                    pass
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        logger.info("Tor stopped.")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _write_torrc(self, path: str) -> None:
        lines = [
            f"DataDirectory {_DATA_DIR}",
            "Log notice stderr",
        ]
        for i in range(self._n):
            lines.append(f"SocksPort {_BASE_SOCKS + i}")
            lines.append(f"ControlPort {_BASE_CONTROL + i}")

        if self._control_pass:
            lines.append("CookieAuthentication 0")
            # User must pre-hash the password:
            # tor --hash-password <pass>  and put result in torrc as HashedControlPassword
            # For simplicity we require them to pass the plaintext and we use it directly
            # (only works if Tor was started with the same plaintext — use cookie auth instead)
        else:
            lines.append("CookieAuthentication 1")

        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _wait_for_control_port(self, timeout: int = 90) -> None:
        """Block until the first control port is reachable."""
        deadline = time.time() + timeout
        port = _BASE_CONTROL
        while time.time() < deadline:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=1)
                s.close()
                logger.info(f"Tor control port {port} reachable.")
                return
            except OSError:
                time.sleep(1)
        raise RuntimeError(f"Tor control port {port} not reachable after {timeout}s.")

    def _connect_controllers(self) -> None:
        try:
            from stem.control import Controller
        except ImportError:
            logger.warning("'stem' not installed — NEWNYM rotation disabled. Run: pip install stem")
            self._controllers = [None] * self._n
            return

        for i in range(self._n):
            port = _BASE_CONTROL + i
            try:
                ctrl = Controller.from_port(port=port)
                if self._control_pass:
                    ctrl.authenticate(password=self._control_pass)
                else:
                    ctrl.authenticate()
                self._controllers.append(ctrl)
                logger.info(f"  [tor:{i}] controller connected (port {port})")
            except Exception as e:
                logger.warning(f"  [tor:{i}] controller failed: {e}")
                self._controllers.append(None)
