"""CSS gradients as PicTex paint sources.

Supports ``linear-gradient``, ``radial-gradient`` and ``conic-gradient`` plus their
``repeating-*`` variants, following the CSS Images Level 3/4 geometry:

* linear: the gradient line length depends on the angle and the box's aspect ratio, and
  corner directions (``to top right``) are perpendicular to the box diagonal;
* radial: circle/ellipse ending shapes, ``closest-side`` / ``closest-corner`` /
  ``farthest-side`` / ``farthest-corner`` and explicit sizes, ``at <position>``;
* conic: ``from <angle>`` and ``at <position>``;
* color stops with %, px (or angles for conic), double positions, out-of-range positions,
  hard stops, and CSS "color stop fixup";
* colors interpolate in premultiplied space, like browsers (``red → transparent`` does not
  turn grey).

Geometry depends on the element's final size, which is only known when painting, so the
classes here implement PicTex's ``PaintSource`` and build the Skia shader from the bounds
PicTex passes to ``apply_to_paint``.
"""
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import skia
from pictex import PaintSource, SolidColor

from ..styling import ColorNormalizer

PREMUL = int(skia.GradientShader.Flags.kInterpolateColorsInPremul_Flag)
GRADIENT_FUNCTIONS = (
    'linear-gradient', 'radial-gradient', 'conic-gradient',
    'repeating-linear-gradient', 'repeating-radial-gradient', 'repeating-conic-gradient',
)

_NUMBER = r'[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?'
_DIMENSION = re.compile(rf'^({_NUMBER})([a-z%]*)$', re.IGNORECASE)
_ANGLE_UNITS = {'deg': 1.0, 'grad': 0.9, 'rad': 180 / math.pi, 'turn': 360.0}


class GradientError(ValueError):
    """Raised for gradient syntax html2pic does not understand."""


# --------------------------------------------------------------------------- values


@dataclass(frozen=True)
class Length:
    """A length/percentage/angle as written in CSS, resolved at paint time."""

    value: float
    unit: str  # '%', 'px', or 'deg' (angles are normalised to degrees)

    def resolve(self, reference: float) -> float:
        """Convert to a fraction of ``reference`` (px) or of a full turn (angles)."""
        if self.unit == '%':
            return self.value / 100
        if self.unit == 'deg':
            return self.value / 360
        return self.value / reference if reference else 0.0


def _parse_dimension(token: str, angles: bool = False) -> Optional[Length]:
    match = _DIMENSION.match(token.strip().lower())
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2)
    if unit == '%':
        return Length(value, '%')
    if angles:
        if unit in _ANGLE_UNITS:
            return Length(value * _ANGLE_UNITS[unit], 'deg')
        if unit == '' and value == 0:
            return Length(0.0, 'deg')
        return None
    if unit == 'px' or (unit == '' and value == 0):
        return Length(value, 'px')
    if unit in ('em', 'rem'):
        # Gradients are resolved after style computation, so use the root font size.
        return Length(value * 16, 'px')
    return None


def parse_angle(token: str) -> Optional[float]:
    """Return an angle in degrees, or None."""
    length = _parse_dimension(token, angles=True)
    return length.value if length is not None and length.unit == 'deg' else None


def _split_top_level(value: str, separator: str) -> List[str]:
    parts, current, depth = [], '', 0
    for char in value:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        if depth == 0 and (char == separator or (separator == ' ' and char.isspace())):
            if current.strip():
                parts.append(current.strip())
            current = ''
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


# --------------------------------------------------------------------------- color stops


@dataclass
class ColorStop:
    color: SolidColor
    position: Optional[Length] = None


_color_normalizer = ColorNormalizer()


def _parse_color(token: str) -> Optional[SolidColor]:
    normalized = _color_normalizer.normalize(token)
    if normalized == 'transparent':
        return SolidColor(0, 0, 0, 0)
    try:
        return SolidColor.from_str(normalized)
    except Exception:
        return None


def _parse_color_stop(text: str, angles: bool) -> Optional[List[ColorStop]]:
    """Parse ``<color> <pos>? <pos>?`` (either order). Returns None if it is not a stop."""
    tokens = _split_top_level(text, ' ')
    color, positions = None, []
    for token in tokens:
        position = _parse_dimension(token, angles)
        if position is not None:
            positions.append(position)
        elif color is None:
            color = _parse_color(token)
            if color is None:
                return None
        else:
            return None
    if color is None or len(positions) > 2:
        return None
    if not positions:
        return [ColorStop(color)]
    return [ColorStop(color, p) for p in positions]


def _parse_stops(parts: Sequence[str], angles: bool) -> List[ColorStop]:
    stops: List[ColorStop] = []
    for part in parts:
        parsed = _parse_color_stop(part, angles)
        if parsed is None:
            if _parse_dimension(part, angles) is not None:
                raise GradientError(f"color interpolation hints ('{part}') are not supported")
            raise GradientError(f"invalid color stop '{part}'")
        stops.extend(parsed)
    if len(stops) < 2:
        raise GradientError("a gradient needs at least two color stops")
    return stops


def resolve_stop_positions(stops: Sequence[ColorStop], reference: float) -> List[float]:
    """CSS color stop fixup: fill in missing positions and make them non-decreasing."""
    positions: List[Optional[float]] = [
        s.position.resolve(reference) if s.position is not None else None for s in stops
    ]
    if positions[0] is None:
        positions[0] = 0.0
    if positions[-1] is None:
        positions[-1] = 1.0

    highest = positions[0]
    for i, p in enumerate(positions):
        if p is not None:
            highest = max(highest, p)
            positions[i] = highest

    i = 0
    while i < len(positions):
        if positions[i] is None:
            start = i - 1
            end = i
            while positions[end] is None:
                end += 1
            step = (positions[end] - positions[start]) / (end - start)
            for k in range(start + 1, end):
                positions[k] = positions[start] + step * (k - start)
            i = end
        i += 1
    return positions  # type: ignore[return-value]


def _argb(color: SolidColor) -> int:
    return skia.Color(color.r, color.g, color.b, color.a)


def _lerp_color(a: SolidColor, b: SolidColor, t: float) -> SolidColor:
    # Premultiplied interpolation, then un-premultiply (matches PREMUL shaders).
    aa, ba = a.a / 255, b.a / 255
    alpha = aa + (ba - aa) * t
    if alpha <= 0:
        return SolidColor(0, 0, 0, 0)
    channels = [((ca * aa) + ((cb * ba) - (ca * aa)) * t) / alpha for ca, cb in ((a.r, b.r), (a.g, b.g), (a.b, b.b))]
    return SolidColor(*[max(0, min(255, round(c))) for c in channels], round(alpha * 255))


def _clip_start(colors: List[SolidColor], positions: List[float], minimum: float) -> Tuple[List[SolidColor], List[float]]:
    """Drop the part of a gradient below ``minimum``, interpolating the color there."""
    if positions[0] >= minimum:
        return colors, positions
    for i in range(1, len(positions)):
        if positions[i] >= minimum:
            span = positions[i] - positions[i - 1]
            t = (minimum - positions[i - 1]) / span if span else 1.0
            edge = _lerp_color(colors[i - 1], colors[i], t)
            return [edge] + colors[i:], [minimum] + positions[i:]
    return [colors[-1], colors[-1]], [minimum, minimum]


def _clip_end(colors: List[SolidColor], positions: List[float], maximum: float) -> Tuple[List[SolidColor], List[float]]:
    reversed_colors, negated = _clip_start(colors[::-1], [-p for p in positions[::-1]], -maximum)
    return reversed_colors[::-1], [-p for p in negated[::-1]]


def _normalized(positions: Sequence[float]) -> Tuple[float, float, List[float]]:
    """Map positions onto [0, 1]; returns (start, end, normalized)."""
    start, end = positions[0], positions[-1]
    span = end - start
    if span <= 1e-9:
        # All stops at one position: CSS renders the last color everywhere past it.
        return start, start + 1e-6, [0.0] * (len(positions) - 1) + [1.0]
    return start, end, [(p - start) / span for p in positions]


# --------------------------------------------------------------------------- positions


def _parse_position(tokens: Sequence[str]) -> Tuple[Length, Length]:
    """Parse a 1- or 2-value <position> into (x, y) lengths."""
    keywords_x = {'left': Length(0, '%'), 'center': Length(50, '%'), 'right': Length(100, '%')}
    keywords_y = {'top': Length(0, '%'), 'center': Length(50, '%'), 'bottom': Length(100, '%')}
    tokens = [t.lower() for t in tokens]
    if len(tokens) == 1:
        token = tokens[0]
        if token in keywords_y and token != 'center':
            return Length(50, '%'), keywords_y[token]
        x = keywords_x.get(token) or _parse_dimension(token)
        if x is None:
            raise GradientError(f"invalid position '{token}'")
        return x, Length(50, '%')
    if len(tokens) == 2:
        first, second = tokens
        if first in ('top', 'bottom') or second in ('left', 'right'):
            first, second = second, first
        x = keywords_x.get(first) or _parse_dimension(first)
        y = keywords_y.get(second) or _parse_dimension(second)
        if x is None or y is None:
            raise GradientError(f"invalid position '{' '.join(tokens)}'")
        return x, y
    raise GradientError(f"positions with {len(tokens)} values are not supported")


def _resolve_point(position: Tuple[Length, Length], bounds: skia.Rect) -> Tuple[float, float]:
    x, y = position
    return (
        bounds.left() + x.resolve(bounds.width()) * bounds.width(),
        bounds.top() + y.resolve(bounds.height()) * bounds.height(),
    )


# --------------------------------------------------------------------------- gradients


@dataclass
class _Gradient(PaintSource):
    stops: List[ColorStop]
    repeating: bool = False

    @property
    def _tile_mode(self) -> skia.TileMode:
        return skia.TileMode.kRepeat if self.repeating else skia.TileMode.kClamp

    def apply_to_paint(self, paint: skia.Paint, bounds: skia.Rect) -> None:
        paint.setShader(self.make_shader(bounds))

    def make_shader(self, bounds: skia.Rect) -> skia.Shader:  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass
class CssLinearGradient(_Gradient):
    # Either an angle in degrees, or a corner like ('top', 'right') resolved at paint time.
    angle: float = 180.0
    corner: Optional[Tuple[str, str]] = None

    def gradient_angle(self, width: float, height: float) -> float:
        if self.corner is None:
            return self.angle
        vertical, horizontal = self.corner
        base = math.degrees(math.atan2(height, width))  # angle that is perpendicular to the diagonal
        return {
            ('top', 'right'): base,
            ('bottom', 'right'): 180 - base,
            ('bottom', 'left'): 180 + base,
            ('top', 'left'): 360 - base,
        }[(vertical, horizontal)]

    def make_shader(self, bounds: skia.Rect) -> skia.Shader:
        w, h = bounds.width(), bounds.height()
        theta = math.radians(self.gradient_angle(w, h))
        dx, dy = math.sin(theta), -math.cos(theta)
        length = abs(w * dx) + abs(h * dy)
        cx, cy = bounds.centerX(), bounds.centerY()

        positions = resolve_stop_positions(self.stops, length)
        start, end, normalized = _normalized(positions)

        def point(t: float) -> skia.Point:
            return skia.Point(cx + dx * (t - 0.5) * length, cy + dy * (t - 0.5) * length)

        return skia.GradientShader.MakeLinear(
            [point(start), point(end)],
            [_argb(s.color) for s in self.stops],
            normalized,
            self._tile_mode,
            PREMUL,
        )


@dataclass
class CssRadialGradient(_Gradient):
    shape: str = 'ellipse'  # 'circle' | 'ellipse'
    extent: str = 'farthest-corner'  # keyword, or 'explicit'
    size: Tuple[Length, ...] = ()
    position: Tuple[Length, Length] = field(default_factory=lambda: (Length(50, '%'), Length(50, '%')))

    def radii(self, bounds: skia.Rect, cx: float, cy: float) -> Tuple[float, float]:
        w, h = bounds.width(), bounds.height()
        if self.extent == 'explicit':
            if self.shape == 'circle':
                r = self.size[0].resolve(1) if self.size[0].unit == 'px' else 0
                return r, r
            return self.size[0].resolve(w) * w, self.size[1].resolve(h) * h

        left, right = cx - bounds.left(), bounds.right() - cx
        top, bottom = cy - bounds.top(), bounds.bottom() - cy
        pick = min if self.extent.startswith('closest') else max
        side_x, side_y = pick(left, right), pick(top, bottom)

        if self.extent.endswith('side'):
            if self.shape == 'circle':
                r = pick(left, right, top, bottom)
                return r, r
            return side_x, side_y

        # closest-corner / farthest-corner
        if self.shape == 'circle':
            corners = [math.hypot(x, y) for x in (left, right) for y in (top, bottom)]
            r = pick(corners)
            return r, r
        # The ellipse keeps the aspect ratio of the matching '-side' ellipse and passes
        # through the corner, which scales both radii by sqrt(2).
        return side_x * math.sqrt(2), side_y * math.sqrt(2)

    def make_shader(self, bounds: skia.Rect) -> skia.Shader:
        cx, cy = _resolve_point(self.position, bounds)
        rx, ry = self.radii(bounds, cx, cy)
        rx, ry = max(rx, 1e-3), max(ry, 1e-3)

        positions = resolve_stop_positions(self.stops, rx)
        colors = [s.color for s in self.stops]
        if self.repeating:
            # Shift by whole periods so the pattern starts at a non-negative radius.
            period = positions[-1] - positions[0]
            if period > 1e-9 and positions[0] < 0:
                shift = math.ceil(-positions[0] / period) * period
                positions = [p + shift for p in positions]
        else:
            colors, positions = _clip_start(colors, positions, 0.0)
        start, end, normalized = _normalized(positions)

        matrix = skia.Matrix()
        matrix.setScale(1, ry / rx, cx, cy)
        center = skia.Point(cx, cy)
        return skia.GradientShader.MakeTwoPointConical(
            center, max(start, 0.0) * rx, center, end * rx,
            [_argb(c) for c in colors], normalized, self._tile_mode, PREMUL, matrix,
        )


@dataclass
class CssConicGradient(_Gradient):
    from_angle: float = 0.0
    position: Tuple[Length, Length] = field(default_factory=lambda: (Length(50, '%'), Length(50, '%')))

    def make_shader(self, bounds: skia.Rect) -> skia.Shader:
        cx, cy = _resolve_point(self.position, bounds)
        positions = resolve_stop_positions(self.stops, 1.0)
        colors = [s.color for s in self.stops]
        if not self.repeating:
            colors, positions = _clip_start(colors, positions, 0.0)
            colors, positions = _clip_end(colors, positions, 1.0)
        start, end, normalized = _normalized(positions)

        # Skia sweeps start at 3 o'clock; CSS conic gradients start at 12 o'clock.
        matrix = skia.Matrix.RotateDeg(self.from_angle - 90, skia.Point(cx, cy))
        return skia.GradientShader.MakeSweep(
            cx, cy, [_argb(c) for c in colors], normalized, self._tile_mode,
            start * 360, end * 360, PREMUL, matrix,
        )


@dataclass
class BackgroundLayers(PaintSource):
    """A background color painted underneath a gradient, as CSS backgrounds do."""

    color: SolidColor
    gradient: PaintSource

    def apply_to_paint(self, paint: skia.Paint, bounds: skia.Rect) -> None:
        self.gradient.apply_to_paint(paint, bounds)
        gradient_shader = paint.getShader()
        paint.setShader(skia.Shaders.Blend(skia.BlendMode.kSrcOver, skia.Shaders.Color(_argb(self.color)), gradient_shader))


# --------------------------------------------------------------------------- parsing


def is_gradient(value: str) -> bool:
    return value.strip().lower().startswith(tuple(f + '(' for f in GRADIENT_FUNCTIONS))


def parse_gradient(value: str) -> _Gradient:
    """Parse a CSS gradient function. Raises GradientError for unsupported syntax."""
    value = value.strip()
    name, _, rest = value.partition('(')
    name = name.strip().lower()
    if name not in GRADIENT_FUNCTIONS or not rest.endswith(')'):
        raise GradientError(f"not a gradient: '{value}'")
    repeating = name.startswith('repeating-')
    kind = name[len('repeating-'):] if repeating else name
    parts = _split_top_level(rest[:-1], ',')
    if not parts:
        raise GradientError("empty gradient")

    angles = kind == 'conic-gradient'
    # A color hint can never come first, so anything that is not a color stop is the configuration.
    has_config = _parse_color_stop(parts[0], angles) is None
    config = _split_top_level(parts[0], ' ') if has_config else []
    stops = _parse_stops(parts[1:] if has_config else parts, angles)

    if kind == 'linear-gradient':
        return _linear(config, stops, repeating)
    if kind == 'radial-gradient':
        return _radial(config, stops, repeating)
    return _conic(config, stops, repeating)


def _linear(config: List[str], stops: List[ColorStop], repeating: bool) -> CssLinearGradient:
    if not config:
        return CssLinearGradient(stops, repeating)
    lowered = [t.lower() for t in config]
    if lowered[0] == 'to':
        sides = lowered[1:]
        single = {'top': 0.0, 'right': 90.0, 'bottom': 180.0, 'left': 270.0}
        if len(sides) == 1 and sides[0] in single:
            return CssLinearGradient(stops, repeating, angle=single[sides[0]])
        if len(sides) == 2:
            vertical = next((s for s in sides if s in ('top', 'bottom')), None)
            horizontal = next((s for s in sides if s in ('left', 'right')), None)
            if vertical and horizontal:
                return CssLinearGradient(stops, repeating, corner=(vertical, horizontal))
        raise GradientError(f"invalid direction '{' '.join(config)}'")
    if len(config) == 1:
        angle = parse_angle(config[0])
        if angle is not None:
            return CssLinearGradient(stops, repeating, angle=angle)
    raise GradientError(f"invalid linear-gradient direction '{' '.join(config)}'")


_EXTENTS = {'closest-side', 'closest-corner', 'farthest-side', 'farthest-corner'}


def _radial(config: List[str], stops: List[ColorStop], repeating: bool) -> CssRadialGradient:
    lowered = [t.lower() for t in config]
    position_tokens: List[str] = []
    if 'at' in lowered:
        index = lowered.index('at')
        position_tokens = config[index + 1:]
        lowered = lowered[:index]

    shape: Optional[str] = None
    extent: Optional[str] = None
    sizes: List[Length] = []
    for token in lowered:
        if token in ('circle', 'ellipse') and shape is None:
            shape = token
        elif token in _EXTENTS and extent is None and not sizes:
            extent = token
        else:
            size = _parse_dimension(token)
            if size is None or extent is not None:
                raise GradientError(f"invalid radial-gradient shape/size '{' '.join(config)}'")
            sizes.append(size)

    if sizes:
        if len(sizes) == 1:
            if shape == 'ellipse' or sizes[0].unit == '%':
                raise GradientError("a single radial-gradient size must be a length and makes a circle")
            shape = 'circle'
        elif len(sizes) == 2:
            if shape == 'circle':
                raise GradientError("a circle takes a single size")
            shape = 'ellipse'
        else:
            raise GradientError("too many radial-gradient sizes")
        extent = 'explicit'

    gradient = CssRadialGradient(
        stops, repeating,
        shape=shape or 'ellipse',
        extent=extent or 'farthest-corner',
        size=tuple(sizes),
    )
    if position_tokens:
        gradient.position = _parse_position(position_tokens)
    return gradient


def _conic(config: List[str], stops: List[ColorStop], repeating: bool) -> CssConicGradient:
    gradient = CssConicGradient(stops, repeating)
    lowered = [t.lower() for t in config]
    if 'at' in lowered:
        index = lowered.index('at')
        gradient.position = _parse_position(config[index + 1:])
        lowered = lowered[:index]
    if lowered:
        if len(lowered) != 2 or lowered[0] != 'from' or parse_angle(lowered[1]) is None:
            raise GradientError(f"invalid conic-gradient configuration '{' '.join(config)}'")
        gradient.from_angle = parse_angle(lowered[1])
    return gradient
