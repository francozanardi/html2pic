"""Ready-made fetchers for :class:`html2pic.Html2Pic`.

A fetcher is any callable ``(url: str) -> bytes`` that raises on failure. html2pic never
loads external stylesheets or remote resources unless a fetcher is given, because the HTML
being rendered may come from an untrusted source.

Example::

    from html2pic import Html2Pic
    from html2pic.fetchers import local_fetcher, http_fetcher, chain_fetchers

    fetcher = chain_fetchers(local_fetcher("./templates"), http_fetcher(timeout=5))
    Html2Pic(html, base_url="./templates/", fetcher=fetcher).render()
"""
import os
from pathlib import Path
from typing import Iterable, Union
from urllib.parse import unquote, urlparse
from urllib.request import Request, url2pathname, urlopen

from .loader import Fetcher

DEFAULT_MAX_BYTES = 20 * 1024 * 1024


class FetchError(Exception):
    """Raised by the bundled fetchers when a resource is refused or cannot be loaded."""


def local_fetcher(root: Union[str, Path]) -> Fetcher:
    """Read ``file://`` URLs, but only for files inside ``root`` (no path traversal)."""
    root_path = Path(root).expanduser().resolve()

    def fetch(url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme != "file":
            raise FetchError(f"local_fetcher only reads file:// URLs, got '{url}'")
        raw = unquote(parsed.path)
        path = Path(url2pathname(raw) if os.name == "nt" else raw).resolve()
        if path != root_path and root_path not in path.parents:
            raise FetchError(f"'{path}' is outside of the allowed directory '{root_path}'")
        return path.read_bytes()

    return fetch


def http_fetcher(
    timeout: float = 10.0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allowed_schemes: Iterable[str] = ("https", "http"),
    user_agent: str = "html2pic",
) -> Fetcher:
    """Download ``http(s)://`` URLs with a timeout and a maximum response size."""
    schemes = tuple(allowed_schemes)

    def fetch(url: str) -> bytes:
        if urlparse(url).scheme not in schemes:
            raise FetchError(f"http_fetcher only loads {'/'.join(schemes)} URLs, got '{url}'")
        request = Request(url, headers={"User-Agent": user_agent})
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme checked above
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise FetchError(f"'{url}' is larger than {max_bytes} bytes")
        return data

    return fetch


def chain_fetchers(*fetchers: Fetcher) -> Fetcher:
    """Try each fetcher in order and return the first successful result."""
    if not fetchers:
        raise ValueError("chain_fetchers() needs at least one fetcher")

    def fetch(url: str) -> bytes:
        errors = []
        for fetcher in fetchers:
            try:
                return fetcher(url)
            except Exception as e:
                errors.append(str(e))
        raise FetchError("; ".join(errors))

    return fetch
