"""Vertical margin collapsing (CSS 2.1 §8.3.1) for block containers.

PicTex lays everything out with flexbox, where margins never collapse. Block containers in
html2pic are flex columns, so this pass rewrites the computed margins to what block layout
would produce before translation:

* adjacent block-level siblings: the larger margin wins (positive margins: max; negative
  margins: min; mixed: their sum);
* a parent and its first/last in-flow child, when no border, padding or content separates
  them and the parent doesn't establish a new block formatting context: the child's margin
  moves to the parent.

Not handled: margins collapsing *through* empty blocks, and clearance (no floats).
"""
from typing import List, Optional

from ..dom import DOMNode

_BLOCK_LEVEL = {'block', 'flex'}


def collapse_margins(root: DOMNode):
    """Apply margin collapsing to a styled tree. ``root`` is the document's root box."""
    _visit(root, is_root=True)


def _visit(node: DOMNode, is_root: bool = False):
    for child in node.children:
        if child.is_element():
            _visit(child)

    if not _is_block_container(node):
        return

    _collapse_siblings(node)
    if not is_root and not _establishes_bfc(node):
        _collapse_with_first_child(node)
        _collapse_with_last_child(node)


# --------------------------------------------------------------------------- rules


def _is_block_container(node: DOMNode) -> bool:
    return node.is_element() and node.computed_styles.get('display') == 'block'


def _establishes_bfc(node: DOMNode) -> bool:
    """Block formatting context roots keep their children's margins inside."""
    styles = node.computed_styles
    parent = node.parent
    return (
        parent is None
        or parent.computed_styles.get('display') == 'flex'  # flex items are BFC roots
        or styles.get('position') in ('absolute', 'fixed')
        or styles.get('overflow-x', 'visible') != 'visible'
        or styles.get('overflow-y', 'visible') != 'visible'
    )


def _in_flow(node: DOMNode) -> bool:
    if node.is_text():
        return True
    styles = node.computed_styles
    return styles.get('display') != 'none' and styles.get('position') not in ('absolute', 'fixed')


def _is_block_level(node: DOMNode) -> bool:
    return node.is_element() and node.computed_styles.get('display') in _BLOCK_LEVEL


def _is_separator(node: DOMNode) -> bool:
    """Content that sits between margins (text or inline boxes) and prevents collapsing."""
    if node.is_text():
        return bool(node.text_content.strip())
    return not _is_block_level(node)


def _collapse_siblings(node: DOMNode):
    previous: Optional[DOMNode] = None
    for child in node.children:
        if not _in_flow(child):
            continue
        if _is_separator(child):
            previous = None
            continue
        if not _is_block_level(child):
            continue
        if previous is not None:
            above, below = _px(previous, 'margin-bottom'), _px(child, 'margin-top')
            if above is not None and below is not None:
                _set(previous, 'margin-bottom', 0.0)
                _set(child, 'margin-top', _combine(above, below))
        previous = child


def _collapse_with_first_child(node: DOMNode):
    if _px(node, 'padding-top') != 0 or _px(node, 'border-width') != 0:
        return
    child = _edge_child(node.children)
    if child is None:
        return
    own, inner = _px(node, 'margin-top'), _px(child, 'margin-top')
    if own is not None and inner is not None:
        _set(node, 'margin-top', _combine(own, inner))
        _set(child, 'margin-top', 0.0)


def _collapse_with_last_child(node: DOMNode):
    styles = node.computed_styles
    if _px(node, 'padding-bottom') != 0 or _px(node, 'border-width') != 0:
        return
    if styles.get('height', 'auto') != 'auto' or styles.get('min-height', 'auto') not in ('auto', '0px'):
        return
    child = _edge_child(list(reversed(node.children)))
    if child is None:
        return
    own, inner = _px(node, 'margin-bottom'), _px(child, 'margin-bottom')
    if own is not None and inner is not None:
        _set(node, 'margin-bottom', _combine(own, inner))
        _set(child, 'margin-bottom', 0.0)


def _edge_child(children: List[DOMNode]) -> Optional[DOMNode]:
    """First in-flow child if it is a block box with nothing before it, else None."""
    for child in children:
        if not _in_flow(child):
            continue
        if child.is_text() and not child.text_content.strip():
            continue
        return child if _is_block_level(child) else None
    return None


# --------------------------------------------------------------------------- helpers


def _combine(a: float, b: float) -> float:
    return max(a, b, 0.0) + min(a, b, 0.0)


def _px(node: DOMNode, prop: str) -> Optional[float]:
    value = node.computed_styles.get(prop, '0px')
    if not isinstance(value, str) or not value.endswith('px'):
        return None
    try:
        return float(value[:-2])
    except ValueError:
        return None


def _set(node: DOMNode, prop: str, value: float):
    node.computed_styles[prop] = f'{value}px'
