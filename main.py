# main.py
import sys
import os
import time
import logging
import threading
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import (
    INSTANCES, EXAM_URLS, OPEN_TIME,
    PROXY_MODE,
    DATAIMPULSE_HOST, DATAIMPULSE_PORT, DATAIMPULSE_USER, DATAIMPULSE_PASS,
    TOR_PATH, TOR_CONTROL_PASS,
)
from rotating_proxy import RotatingProxyServer
from proxy import get_working_proxies
from instance import run_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_open_time(raw: str) -> datetime | None:
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(raw, fmt)
            now = datetime.now()
            target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        except ValueError:
            continue
    return None


def wait_until(target: datetime) -> None:
    while True:
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            print(f"\r  Starting now!{' ' * 30}")
            break
        mins, secs = divmod(int(remaining), 60)
        print(f"\r  Waiting until {target.strftime('%H:%M')} — {mins:02d}:{secs:02d} remaining…",
              end="", flush=True)
        time.sleep(1)


def assign_urls(urls: list[str], n: int) -> list[str]:
    """Round-robin: 1 URL → all instances use it; N URLs → distribute evenly."""
    if len(urls) == 1:
        return [urls[0]] * n
    return [urls[i % len(urls)] for i in range(n)]


# ── Input prompts ─────────────────────────────────────────────────────────────

def _prompt_instances() -> int:
    val = input(f"  How many browser instances? [{INSTANCES}]: ").strip()
    if not val:
        return INSTANCES
    try:
        n = int(val)
        return max(1, n)
    except ValueError:
        print("  Invalid — using 1.")
        return 1


def _prompt_urls() -> list[str]:
    if EXAM_URLS:
        print(f"  URLs from .env ({len(EXAM_URLS)}): {', '.join(EXAM_URLS)}")
        override = input("  Press Enter to use these, or paste new URLs (comma-separated): ").strip()
        if not override:
            return EXAM_URLS
        raw = override
    else:
        raw = input("  Paste exam URL(s), comma-separated: ").strip()

    urls = [u.strip() for u in raw.split(",") if u.strip()]
    invalid = [u for u in urls if not u.startswith("http")]
    if invalid:
        print(f"  Invalid URLs (must start with https://): {invalid}")
        sys.exit(1)
    if not urls:
        print("  No URLs provided.")
        sys.exit(1)
    return urls


def _prompt_open_time() -> str:
    default = OPEN_TIME or ""
    hint = default if default else "immediate"
    val = input(f"  Booking opens at HH:MM (24h) [{hint}]: ").strip()
    return val or default


def _prompt_proxy_mode() -> str:
    print(f"\n  Proxy mode from .env: {PROXY_MODE}")
    print("  Options: none | free | dataimpulse | tor")
    override = input("  Override proxy mode? [Enter to keep]: ").strip().lower()
    return override if override in ("none", "free", "dataimpulse", "tor") else PROXY_MODE


# ── Proxy setup ───────────────────────────────────────────────────────────────

def setup_proxy(n: int, mode: str):
    """
    Returns (proxy_addrs, rps, tor_manager).
    proxy_addrs[i] is the proxy string for instance i, or None for direct.
    """
    if mode == "none":
        logger.info("Proxy: none — direct connection.")
        return [None] * n, None, None

    if mode == "dataimpulse":
        return _proxy_dataimpulse(n)

    if mode == "free":
        return _proxy_free(n)

    if mode == "tor":
        return _proxy_tor(n)

    logger.warning(f"Unknown proxy mode '{mode}' — direct connection.")
    return [None] * n, None, None


def _proxy_dataimpulse(n: int):
    user = DATAIMPULSE_USER or input("  DataImpulse username: ").strip()
    pwd  = DATAIMPULSE_PASS or input("  DataImpulse password: ").strip()
    if not user or not pwd:
        logger.warning("No DataImpulse credentials — direct connection.")
        return [None] * n, None, None

    endpoint = f"{DATAIMPULSE_HOST}:{DATAIMPULSE_PORT}"
    # All instances share ONE RotatingProxyServer.
    # DataImpulse assigns a fresh residential IP per CONNECT tunnel automatically.
    rps = RotatingProxyServer([endpoint], auth=f"{user}:{pwd}")
    rps.start()
    addr = f"127.0.0.1:{rps.port}"
    logger.info(f"DataImpulse proxy → {addr}  (upstream: {endpoint})")
    return [addr] * n, rps, None


def _proxy_free(n: int):
    logger.info("Fetching free proxies…")
    # Fetch enough for all instances plus spares
    proxies = get_working_proxies(n=max(n * 3, 20), limit=150)
    if not proxies:
        print("  Auto-fetch failed. Paste proxies manually (ip:port, blank line to finish):")
        proxies = []
        while True:
            line = input("    proxy> ").strip()
            if not line:
                break
            proxies.append(line)

    if not proxies:
        logger.warning("No proxies available — direct connection.")
        return [None] * n, None, None

    rps = RotatingProxyServer(proxies)
    rps.start()
    addr = f"127.0.0.1:{rps.port}"
    logger.info(f"Free proxy pool ({len(proxies)} upstreams) → {addr}")
    return [addr] * n, rps, None


def _proxy_tor(n: int):
    if not TOR_PATH or not os.path.exists(TOR_PATH):
        print(f"\n  Tor binary not found. TOR_PATH='{TOR_PATH}'")
        print("  Download the Tor Expert Bundle from https://www.torproject.org/download/tor/")
        print("  Then set TOR_PATH in your .env file.")
        sys.exit(1)

    from tor_manager import TorManager
    tm = TorManager(n_instances=n, tor_path=TOR_PATH, control_pass=TOR_CONTROL_PASS)
    try:
        tm.start()
    except Exception as e:
        logger.error(f"Tor failed to start: {e}")
        sys.exit(1)

    addrs = [tm.socks_addr(i) for i in range(n)]
    logger.info(f"Tor: {n} circuits active")
    return addrs, None, tm


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("\n" + "=" * 60)
    print("  Goethe B2 Booking Bot  (multi-instance)")
    print("=" * 60 + "\n")

    n         = _prompt_instances()
    urls      = _prompt_urls()
    open_time = _prompt_open_time()
    mode      = _prompt_proxy_mode()

    assigned = assign_urls(urls, n)
    proxy_addrs, rps, tor_manager = setup_proxy(n, mode)

    logger.info(f"Launching {n} instance(s) | proxy={mode}")
    for i in range(n):
        logger.info(f"  [{i}] url={assigned[i]}  proxy={proxy_addrs[i] or 'direct'}")

    # Warmup: launch Chrome 30 s before open time
    target_dt = None
    if open_time:
        target_dt = parse_open_time(open_time)
        if target_dt:
            logger.info(f"Open time: {target_dt.strftime('%H:%M')}")
            warmup_at = target_dt - timedelta(seconds=30)
            if warmup_at > datetime.now():
                print(f"\nWaiting until {warmup_at.strftime('%H:%M')} to launch Chrome…")
                wait_until(warmup_at)
                print()
        else:
            logger.warning(f"Could not parse '{open_time}' — starting immediately.")

    stop_event    = threading.Event()
    success_event = threading.Event()

    threads = []
    for i in range(n):
        t = threading.Thread(
            target=run_instance,
            args=(i, assigned[i], proxy_addrs[i], stop_event, success_event, tor_manager),
            name=f"instance-{i}",
            daemon=True,
        )
        threads.append(t)

    # Stagger launches by 2 s each to avoid Chrome / profile collisions
    for i, t in enumerate(threads):
        t.start()
        logger.info(f"Instance {i} started.")
        if i < n - 1:
            time.sleep(2)

    logger.info(f"All {n} instance(s) running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(5)
            if success_event.is_set():
                logger.info("A slot was booked! Keep the successful Chrome window open for login.")
    except KeyboardInterrupt:
        logger.info("Stopping…")
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=10)
        if rps:
            rps.stop()
        if tor_manager:
            tor_manager.stop()
        logger.info("Done.")


if __name__ == "__main__":
    run()
