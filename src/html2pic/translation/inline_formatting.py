"""Inline formatting: lay out runs of inline content as rich text.

In CSS, consecutive inline-level content inside a block container (text, ``<b>``,
``<span>``, ``<a>``, ``<br>``, inline ``::before``/``::after``...) flows together in lines.
html2pic maps each such run to a single PicTex ``Text`` whose ``Span``s carry the
typography of the inline elements, so a paragraph like ``Hello <b>bold</b> text`` renders
on one line and wraps as a whole.

PicTex spans only support typography. Inline elements that need a box (background,
padding, border, a size, ...) and images are *atomic*: a run containing them is laid out
as a wrapping row of text pieces and boxes, which approximates inline flow for short
content such as an icon next to a label.
"""
import re
from typing import Callable, Dict, List, Optional, Tuple

from pictex import Element, Row, Span, Text

from ..dom import DOMNode
from ..styling import DEFAULT_STYLES

_WHITESPACE = re.compile(r'[ \t\n\r\f]+')

# Computed values that mean an inline element has no box of its own.
_BOXLESS = {
    'background-color': 'transparent',
    'background-image': 'none',
    'box-shadow': 'none',
    'border-width': '0px',
    'width': 'auto',
    'height': 'auto',
    'position': 'static',
    'transform': 'none',
    'overflow-x': 'visible',
    'overflow-y': 'visible',
}
_ZERO_SIDES = [
    f'{box}-{side}' for box in ('padding', 'margin') for side in ('top', 'right', 'bottom', 'left')
]
_TEXT_ALIGN_TO_JUSTIFY = {'left': 'start', 'center': 'center', 'right': 'end', 'justify': 'start'}


def is_inline_level(node: DOMNode) -> bool:
    if node.is_text():
        return True
    return node.computed_styles.get('display') == 'inline'


def is_text_like(node: DOMNode) -> bool:
    """True if the node can be expressed as (nested) PicTex spans."""
    if node.is_text():
        return True
    styles = node.computed_styles
    if styles.get('display') == 'none':
        return True
    if styles.get('display') != 'inline' or node.tag == 'img':
        return False
    if node.tag == 'br':
        return True
    for prop, value in _BOXLESS.items():
        if styles.get(prop, DEFAULT_STYLES.get(prop, value)) != value:
            return False
    if any(_px(styles.get(prop, '0px')) != 0 for prop in _ZERO_SIDES):
        return False
    return all(is_text_like(child) for child in node.children)


def _px(value: str) -> float:
    try:
        return float(value[:-2]) if value.endswith('px') else float(value)
    except ValueError:
        return 1.0  # unknown units: treat as a box


class InlineFormatter:
    """Builds PicTex elements for runs of inline content."""

    def __init__(
        self,
        style_text: Callable[[Text, Dict], Text],
        style_span: Callable[[Span, Dict], Span],
        translate_atomic: Callable[[DOMNode], Optional[Element]],
    ):
        self._style_text = style_text
        self._style_span = style_span
        self._translate_atomic = translate_atomic

    # ------------------------------------------------------------------ public

    def build(self, run: List[DOMNode], container: DOMNode) -> Optional[Element]:
        """Lay out a run of inline-level siblings that belong to ``container``."""
        texts = self._collapse_whitespace(run)
        if all(is_text_like(node) for node in run):
            return self._text(run, texts, container.computed_styles)

        # Atomic inline boxes present: text pieces and boxes in a wrapping row.
        items: List[Element] = []
        pending: List[DOMNode] = []
        for node in run:
            if is_text_like(node):
                pending.append(node)
                continue
            if pending:
                items.extend(filter(None, [self._text(pending, texts, container.computed_styles)]))
                pending = []
            box = self._translate_atomic(node)
            if box is not None:
                items.append(box)
        if pending:
            items.extend(filter(None, [self._text(pending, texts, container.computed_styles)]))
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        align = container.computed_styles.get('text-align', 'left')
        return (
            Row(*items)
            .flex_wrap('wrap')
            .align_items('center')
            .justify_content(_TEXT_ALIGN_TO_JUSTIFY.get(align, 'start'))
        )

    # ------------------------------------------------------------------ text

    def _text(self, nodes: List[DOMNode], texts: Dict[int, str], styles: Dict) -> Optional[Text]:
        items = self._items(nodes, texts)
        if not items:
            return None
        return self._style_text(Text(*items), styles)

    def _items(self, nodes: List[DOMNode], texts: Dict[int, str]) -> List:
        items: List = []
        for node in nodes:
            if node.is_text():
                text = texts.get(id(node), '')
                if text:
                    items.append(text)
            elif node.computed_styles.get('display') == 'none':
                continue
            elif node.tag == 'br':
                items.append('\n')
            else:
                children = self._items(node.children, texts)
                if children:
                    items.append(self._style_span(Span(*children), node.computed_styles))
        return items

    # ------------------------------------------------------------------ whitespace

    def _collapse_whitespace(self, run: List[DOMNode]) -> Dict[int, str]:
        """Collapse whitespace across the run like CSS ``white-space: normal``.

        Returns the rendered text of every text node, keyed by ``id(node)``.
        """
        sequence: List[Tuple[str, Optional[DOMNode]]] = []

        def walk(node: DOMNode):
            if node.is_text():
                sequence.append(('text', node))
            elif node.computed_styles.get('display') == 'none':
                return
            elif node.tag == 'br':
                sequence.append(('break', node))
            elif is_text_like(node):
                for child in node.children:
                    walk(child)
            else:
                sequence.append(('atom', node))

        for node in run:
            walk(node)

        texts: Dict[int, str] = {}
        at_line_start = True
        last_text: Optional[DOMNode] = None
        for kind, node in sequence:
            if kind == 'text':
                text = _WHITESPACE.sub(' ', node.text_content)
                if at_line_start:
                    text = text.lstrip(' ')
                texts[id(node)] = text
                if text:
                    at_line_start = text.endswith(' ')
                    last_text = node
            elif kind == 'break':
                if last_text is not None:
                    texts[id(last_text)] = texts[id(last_text)].rstrip(' ')
                at_line_start, last_text = True, None
            else:
                at_line_start, last_text = False, None
        if last_text is not None:
            texts[id(last_text)] = texts[id(last_text)].rstrip(' ')
        return texts
