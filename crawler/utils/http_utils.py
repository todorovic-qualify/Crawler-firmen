"""
HTTP-Hilfsfunktionen: Client mit Retry, Rate-Limiting und robots.txt-Unterstützung.
"""
from __future__ import annotations

import time
import urllib.robotparser
from threading import Lock
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Standard-Header
#DEFAULT_HEADERS = {
#    "User-Agent": (
#        "LeadScout/1.0 (lokales Unternehmens-Recherche-Tool; "
#        "nur öffentliche Daten; kontakt@leadscout.example)"
#    ),
#    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#}

# Standard-Header
DEFAULT_HEADERS = {
    "User-Agent": "LeadScout/1.0 (+https://crawler-firmen.vercel.app; contact: a.todorovic@qualify-ai.de)",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


TIMEOUT = httpx.Timeout(15.0, connect=8.0)


class RateLimiter:
    """Einfacher thread-sicherer Rate-Limiter mit min. Pause zwischen Anfragen."""

    def __init__(self, delay_sek: float = 2.0):
        self._delay = delay_sek
        self._letzte_anfrage: dict[str, float] = {}
        self._lock = Lock()

    def warten(self, host: str) -> None:
        with self._lock:
            jetzt = time.monotonic()
            letzte = self._letzte_anfrage.get(host, 0)
            verstrichen = jetzt - letzte
            if verstrichen < self._delay:
                time.sleep(self._delay - verstrichen)
            self._letzte_anfrage[host] = time.monotonic()


# Globaler Rate-Limiter (kann per CLI überschrieben werden)
_rate_limiter = RateLimiter(delay_sek=2.0)


def rate_limiter_setzen(delay_sek: float) -> None:
    global _rate_limiter
    _rate_limiter = RateLimiter(delay_sek=delay_sek)


class RobotsCache:
    """Cached robots.txt Überprüfungen pro Domain."""

    def __init__(self):
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def erlaubt(self, url: str, user_agent: str = "LeadScout") -> bool:
        """Gibt True zurück wenn robots.txt den Zugriff erlaubt (oder nicht vorhanden)."""
        parsed = urlparse(url)
        basis = f"{parsed.scheme}://{parsed.netloc}"
        if basis not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{basis}/robots.txt")
            try:
                rp.read()
            except Exception:
                # robots.txt nicht abrufbar → erlaubt annehmen
                rp = urllib.robotparser.RobotFileParser()
            self._cache[basis] = rp
        return self._cache[basis].can_fetch(user_agent, url)


_robots_cache = RobotsCache()


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
def get(url: str, client: Optional[httpx.Client] = None, prüfe_robots: bool = True) -> Optional[httpx.Response]:
    """
    Führt einen HTTP-GET mit Rate-Limiting, Retry und robots.txt-Check durch.
    Gibt None zurück wenn abgelehnt oder fehlgeschlagen.
    """
    if prüfe_robots and not _robots_cache.erlaubt(url):
        logger.debug(f"robots.txt verbietet: {url}")
        return None

    host = urlparse(url).netloc
    _rate_limiter.warten(host)

    _client = client or httpx.Client(headers=DEFAULT_HEADERS, timeout=TIMEOUT, follow_redirects=True)
    eigener_client = client is None

    try:
        response = _client.get(url)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} für {url}")
        return None
    except Exception as e:
        logger.warning(f"Fehler beim Abrufen von {url}: {e}")
        raise
    finally:
        if eigener_client:
            _client.close()


def get_json(url: str, params: Optional[dict] = None, timeout: float = 30.0) -> Optional[dict]:
    """JSON-GET ohne robots.txt-Check (für APIs)."""
    host = urlparse(url).netloc
    _rate_limiter.warten(host)
    try:
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"JSON-Abruf fehlgeschlagen {url}: {e}")
        return None


def erstelle_client() -> httpx.Client:
    """Erstellt einen wiederverwendbaren HTTP-Client."""
    return httpx.Client(
        headers=DEFAULT_HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
    )
