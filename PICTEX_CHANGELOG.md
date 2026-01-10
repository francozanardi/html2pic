## [2.0.0] - 2026-01-04

### Added
- **Taffy Layout Engine**: Migrated from custom Python layout to `stretchable` (Taffy bindings), providing robust CSS Flexbox layout with improved performance and correctness.
- **CSS-Compliant Positioning System**: Complete overhaul of positioning methods to match CSS standards:
  - **`absolute_position()`**: Position elements relative to their nearest ancestor (like CSS `position: absolute`). Uses `top`, `right`, `bottom`, `left` inset properties.
  - **`fixed_position()`**: Position elements relative to the canvas viewport, ignoring parent positioning (like CSS `position: fixed`). Uses `top`, `right`, `bottom`, `left` inset properties.
  - **`relative_position()`**: Position elements relative to their normal flow position with visual offsets (like CSS `position: relative`). Uses `top`, `right`, `bottom`, `left` inset properties.
  - **`place()`**: Convenience method for anchor-based positioning. Internally uses `fixed_position()` with automatic translate transforms. Supports keywords (`"center"`, `"left"`, `"right"`, `"top"`, `"bottom"`), pixels, percentages, and offsets.
- **Transform Support**: New `translate()` method for post-layout transforms, enabling true centering with percentage-based offsets (e.g., `translate(x="-50%", y="-50%")`).
- **Flex Control Properties**: New methods for fine-grained flexbox control:
  - `flex_grow(value)`: Control how elements grow to fill available space
  - `flex_shrink(value)`: Control how elements shrink when space is limited
  - `align_self(alignment)`: Override container alignment for individual items
  - `flex_wrap(mode)`: Enable multi-line flex containers for responsive layouts
- **Size Constraints**: New methods for controlling element size boundaries:
  - `min_width(value)`: Set minimum width constraint to prevent collapse
  - `max_width(value)`: Set maximum width constraint to prevent overflow
  - `min_height(value)`: Set minimum height constraint to maintain minimum space
  - `max_height(value)`: Set maximum height constraint to limit vertical growth
  - All constraints support both absolute (pixels) and percentage values
- **Aspect Ratio**: New `aspect_ratio(ratio)` method for maintaining element proportions:
  - Automatically calculates height when width is specified (or vice versa)
  - Supports numeric values (e.g., `16/9`, `1.618`) or string format (e.g., `"16/9"`)

### Changed
- **BREAKING**: `position()` method removed. This method positioned elements relative to their **parent** using anchor-based coordinates.
  - **Migration**: Use `absolute_position(top=, left=, right=, bottom=)` with CSS insets for parent-relative positioning.
- **BREAKING**: `absolute_position()` now uses CSS-style inset properties (`top`, `right`, `bottom`, `left`) instead of positional `(x, y)` arguments. It is now **parent-relative** (like CSS `position: absolute`).
  - **Migration options** for old canvas-relative `absolute_position(x, y)`:
    1. Use `place(x, y)` for anchor-based canvas positioning
    2. Use `fixed_position(top=, left=)` for CSS-style canvas positioning
  - **Understanding the difference**:
    - `absolute_position()` is now **parent-relative** (like CSS `position: absolute`)
    - `fixed_position()` and `place()` are **canvas-relative** (like CSS `position: fixed`)
- **BREAKING**: Layout methods renamed to CSS-compliant names:
  - `horizontal_distribution()` → `justify_content()` (Row)
  - `vertical_distribution()` → `justify_content()` (Column)
  - `vertical_align()` → `align_items()` (Row)
  - `horizontal_align()` → `align_items()` (Column)
- **BREAKING**: Removed `'fill-available'` size mode. Use `flex_grow(1)` instead for flexible sizing.
  - **Migration**: Replace `.size(width='fill-available')` with `.flex_grow(1)`
- **BREAKING**: Positioning logic now strictly follows CSS standards.
- **Layout Engine**: All layout calculations now delegated to Taffy, replacing the custom multi-pass algorithm.

### Fixed
- Improved layout correctness for complex nested flexbox scenarios.
- Better handling of percentage-based sizing and positioning.
- Fixed text wrapping on nested nodes.