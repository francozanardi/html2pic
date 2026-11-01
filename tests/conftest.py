"""Shared fixtures and helpers for the html2pic test suite."""
from typing import Callable, Dict, Any

import pytest

from html2pic import Html2Pic
from html2pic.dom import DOMNode
from html2pic.warnings import get_warning_collector, reset_warnings


@pytest.fixture(autouse=True)
def _isolate_warnings():
    """The warning collector is a module-level singleton; reset it around every test."""
    reset_warnings()
    yield
    reset_warnings()


@pytest.fixture
def warnings_collector():
    return get_warning_collector()


def find_first(node: DOMNode, tag: str) -> DOMNode:
    """Depth-first search for the first element with the given tag."""
    if node.is_element() and node.tag == tag:
        return node
    for child in node.children:
        found = find_first(child, tag)
        if found is not None:
            return found
    return None


@pytest.fixture
def computed() -> Callable[..., Dict[str, Any]]:
    """Return the computed styles of the first ``tag`` element after cascading ``css``."""

    def _computed(html: str, css: str = "", tag: str = "div") -> Dict[str, Any]:
        styled = Html2Pic(html, css).styled_tree
        # Skip the synthetic root wrapper the parser adds around the document.
        node = next((n for n in (find_first(c, tag) for c in styled.children) if n is not None), None)
        assert node is not None, f"no <{tag}> element in {html!r}"
        return node.computed_styles

    return _computed


@pytest.fixture
def render_rgba():
    """Render ``html``/``css`` and return the image as an (h, w, 4) RGBA numpy array."""

    def _render(html: str, css: str = ""):
        return Html2Pic(html, css).render().to_numpy("RGBA")

    return _render
