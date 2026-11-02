"""Public re-export of the bundled fetchers (see :mod:`html2pic.resources.fetchers`)."""
from .resources.fetchers import FetchError, chain_fetchers, http_fetcher, local_fetcher

__all__ = ["FetchError", "chain_fetchers", "http_fetcher", "local_fetcher"]
