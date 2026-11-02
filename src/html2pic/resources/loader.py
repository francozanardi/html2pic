"""Resolution and loading of external resources (stylesheets, images, fonts)."""
import base64
import hashlib
import os
import tempfile
import weakref
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import unquote, unquote_to_bytes, urljoin, urlparse
from urllib.request import url2pathname

from ..warnings import get_warning_collector

Fetcher = Callable[[str], bytes]
"""Takes an absolute URL (``https://...`` or ``file://...``) and returns its content.

It should raise an exception when the resource cannot be loaded.
"""

REMOTE_SCHEMES = ("http", "https")


def _is_windows_drive(url: str) -> bool:
    return len(url) > 2 and url[1] == ":" and url[0].isalpha() and url[2] in "\\/"


def to_url(location: str) -> str:
    """Turn a filesystem path or URL into an absolute URL usable as a resolution base."""
    parsed = urlparse(location)
    if parsed.scheme and not _is_windows_drive(location):
        return location
    path = Path(location).expanduser().resolve()
    uri = path.as_uri()
    # A directory base needs a trailing slash so that urljoin resolves *inside* it.
    if location.endswith(("/", os.sep)) or path.is_dir():
        uri = uri.rstrip("/") + "/"
    return uri


class ResourceLoader:
    """Resolves URLs found in HTML/CSS and turns them into something PicTex can load.

    PicTex only reads local files, so:

    * relative URLs are resolved against the document base (``base_url``) or, inside a
      stylesheet, against that stylesheet's URL;
    * ``file://`` URLs and plain paths become local paths (read by PicTex as before);
    * ``data:`` URIs are decoded into temporary files;
    * remote ``http(s)://`` resources, and stylesheets referenced by ``<link>`` or ``@import``,
      are only loaded through the user-supplied ``fetcher``. Without one they are skipped
      with a warning, so rendering untrusted HTML never triggers network or file access
      the caller did not opt into.
    """

    def __init__(self, base_url: Optional[str] = None, fetcher: Optional[Fetcher] = None):
        self.base_url = to_url(base_url) if base_url else to_url(os.getcwd() + os.sep)
        self.fetcher = fetcher
        self.warnings = get_warning_collector()
        self._tmpdir: Optional[tempfile.TemporaryDirectory] = None
        self._localized: Dict[str, Optional[str]] = {}

    # ------------------------------------------------------------------ resolution

    def resolve(self, url: str, base: Optional[str] = None) -> str:
        """Return ``url`` as an absolute URL, resolved against ``base`` (default: document base)."""
        url = url.strip()
        if url.startswith("data:"):
            return url
        if _is_windows_drive(url):
            return Path(url).resolve().as_uri()
        return urljoin(base or self.base_url, url)

    def set_document_base(self, href: str):
        """Apply an HTML ``<base href>``, which is itself relative to the original base."""
        self.base_url = self.resolve(href)

    # ------------------------------------------------------------------ loading

    def fetch_text(self, url: str, purpose: str) -> Optional[str]:
        """Load a stylesheet. Always goes through the fetcher (never implicit file access)."""
        if url.startswith("data:"):
            data = self._decode_data_uri(url)
            return data.decode("utf-8", errors="replace") if data is not None else None
        if self.fetcher is None:
            self.warnings.warn_resource(
                f"Skipped {purpose} '{url}': pass a `fetcher` to Html2Pic to load external stylesheets"
            )
            return None
        try:
            return self.fetcher(url).decode("utf-8", errors="replace")
        except Exception as e:
            self.warnings.warn_resource(f"Failed to load {purpose} '{url}': {e}")
            return None

    def localize(self, url: str, base: Optional[str] = None, purpose: str = "resource") -> Optional[str]:
        """Return a local filesystem path for an image/font URL, or None if it can't be loaded."""
        absolute = self.resolve(url, base)
        if absolute not in self._localized:
            self._localized[absolute] = self._localize(absolute, purpose)
        return self._localized[absolute]

    def _localize(self, url: str, purpose: str) -> Optional[str]:
        if url.startswith("data:"):
            data = self._decode_data_uri(url)
            return self._store(url, data) if data is not None else None

        parsed = urlparse(url)
        if parsed.scheme == "file":
            return url2pathname(unquote(parsed.path)) if os.name == "nt" else unquote(parsed.path)

        if parsed.scheme in REMOTE_SCHEMES:
            if self.fetcher is None:
                self.warnings.warn_resource(
                    f"Skipped remote {purpose} '{url}': pass a `fetcher` to Html2Pic to load remote resources"
                )
                return None
            try:
                return self._store(url, self.fetcher(url))
            except Exception as e:
                self.warnings.warn_resource(f"Failed to load {purpose} '{url}': {e}")
                return None

        self.warnings.warn_resource(f"Unsupported URL scheme for {purpose}: '{url}'")
        return None

    def _decode_data_uri(self, url: str) -> Optional[bytes]:
        try:
            header, _, payload = url[len("data:"):].partition(",")
            if header.endswith(";base64"):
                return base64.b64decode(payload)
            return unquote_to_bytes(payload)
        except Exception as e:
            self.warnings.warn_resource(f"Invalid data URI: {e}")
            return None

    def _store(self, url: str, data: bytes) -> str:
        if self._tmpdir is None:
            self._tmpdir = tempfile.TemporaryDirectory(prefix="html2pic-")
            weakref.finalize(self, self._tmpdir.cleanup)
        suffix = Path(urlparse(url).path).suffix if not url.startswith("data:") else ""
        name = hashlib.sha256(url.encode()).hexdigest()[:16] + suffix[:10]
        path = Path(self._tmpdir.name) / name
        path.write_bytes(data)
        return str(path)
