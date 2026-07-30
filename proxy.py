# proxy.py
import logging
import random
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

_PROXY_SOURCES = [
    (
        "https://api.proxyscrape.com/v2/"
        "?request=displayproxies&protocol=http&timeout=5000"
        "&country=all&ssl=all&anonymity=all"
    ),
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc&protocols=http",
]


def _parse_proxies(url: str, text: str) -> list[str]:
    """Parse proxy list from a response body (plain text or geonode JSON)."""
    if "geonode.com" in url:
        import json
        data = json.loads(text)
        return [f"{e['ip']}:{e['port']}" for e in data.get("data", []) if e.get("ip") and e.get("port")]
    return [line.strip() for line in text.strip().splitlines() if line.strip()]


def fetch_free_proxies(limit: int = 100) -> list[str]:
    """Fetch a shuffled list of free HTTP proxies (ip:port strings)."""
    for url in _PROXY_SOURCES:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            proxies = _parse_proxies(url, resp.text)
            if proxies:
                random.shuffle(proxies)
                return proxies[:limit]
        except Exception as e:
            logger.warning(f"Proxy source failed ({url}): {e}")
    return []


def test_proxy(proxy: str, timeout: int = 8) -> bool:
    """
    Test via a raw CONNECT tunnel — the same method Chrome uses for HTTPS.
    Many free proxies support plain HTTP but silently fail CONNECT; this catches that.
    """
    try:
        host, port_str = proxy.rsplit(":", 1)
        sock = socket.create_connection((host, int(port_str)), timeout=timeout)
        sock.sendall(b"CONNECT www.goethe.de:443 HTTP/1.1\r\nHost: www.goethe.de:443\r\n\r\n")
        resp = sock.recv(256)
        sock.close()
        return b"200" in resp.split(b"\r\n")[0]
    except Exception:
        return False


def get_working_proxies(n: int = 5, limit: int = 60) -> list[str]:
    """
    Test up to `limit` free proxies in parallel; return up to `n` working ones.
    Uses 20 threads so results come back quickly.
    """
    candidates = fetch_free_proxies(limit)
    if not candidates:
        logger.warning("Could not download any proxy list.")
        return []

    logger.info(f"Testing {len(candidates)} proxies in parallel (need {n})…")
    working: list[str] = []
    done = threading.Event()

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(test_proxy, p): p for p in candidates}
        for fut in as_completed(futures):
            if done.is_set():
                fut.cancel()
                continue
            proxy = futures[fut]
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                working.append(proxy)
                logger.info(f"  + {proxy}  ({len(working)}/{n})")
                if len(working) >= n:
                    done.set()

    logger.info(f"Found {len(working)} working proxy/proxies.")
    return working
