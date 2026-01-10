# Migration Guide: v1.x to v2.0

This guide covers breaking changes introduced in PicTex v2.0 and provides migration paths for existing code.

## Overview

PicTex v2.0 is a major release focused on CSS compliance and layout engine robustness. The update includes:

- **Layout engine**: Migrated to Taffy (via `stretchable` bindings) for production-grade Flexbox layout
- **API standardization**: Method names now align with CSS Flexbox terminology
- **Positioning system**: Redesigned to follow CSS positioning standards

---

## Breaking Changes

### 1. Positioning API

The positioning system has been completely redesigned to follow CSS standards. Both `position()` and `absolute_position()` methods have changed.

#### `position()` removed (parent-relative with anchors)

The old `position(x, y, x_offset, y_offset)` method positioned elements relative to their **parent** using anchor-based coordinates. This has been replaced with CSS-style inset properties.

**Before (v1.x):**
```python
# Position relative to parent with anchor
Text("Badge").position("right", "top", x_offset=-10, y_offset=10)
Text("Badge").position(50, 100)  # Anchor at 50px, 100px from parent
```

**After (v2.0):**
```python
# Use absolute_position for parent-relative positioning with CSS insets
Text("Badge").absolute_position(top=10, right=10)
Text("Badge").absolute_position(top=100, left=50)
```

#### `absolute_position()` signature changed (canvas-relative with anchors)

The old `absolute_position(x, y, x_offset, y_offset)` method positioned elements relative to the **canvas** using anchor-based coordinates. This is now handled by `place()` or `fixed_position()`.

**Before (v1.x):**
```python
# Position relative to canvas with anchor
Text("Watermark").absolute_position("right", "bottom", x_offset=-20, y_offset=-20)
Text("Overlay").absolute_position("center", "center")
```

**After (v2.0):**
```python
# Option A: Use place() for anchor-based canvas positioning
Text("Watermark").place("right", "bottom", x_offset=-20, y_offset=-20)
Text("Overlay").place("center", "center")

# Option B: Use fixed_position() with CSS insets
Text("Watermark").fixed_position(bottom=20, right=20)
```

#### Summary of positioning methods

| v1.x Method | v2.0 Equivalent | Relative To |
|-------------|-----------------|-------------|
| `position(x, y, ...)` | `absolute_position(top=, left=, ...)` | Parent |
| `absolute_position(x, y, ...)` | `place(x, y, ...)` or `fixed_position(...)` | Canvas |

The new `place()` method provides anchor-based positioning:
- Supports keywords: `"left"`, `"center"`, `"right"`, `"top"`, `"bottom"`
- Supports pixels: `place(50, 100)`
- Supports percentages: `place("25%", "75%")`
- Supports offsets: `place("right", "top", x_offset=-10, y_offset=10)`

---

### 2. Layout Method Renaming

Container layout methods have been renamed to match CSS Flexbox terminology.

| v1.x Method | v2.0 Method | Container |
|-------------|-------------|-----------|
| `horizontal_distribution()` | `justify_content()` | `Row` |
| `vertical_distribution()` | `justify_content()` | `Column` |
| `vertical_align()` | `align_items()` | `Row` |
| `horizontal_align()` | `align_items()` | `Column` |

**Before (v1.x):**
```python
Row(children).horizontal_distribution("center").vertical_align("center")
Column(children).vertical_distribution("space-between").horizontal_align("stretch")
```

**After (v2.0):**
```python
Row(children).justify_content("center").align_items("center")
Column(children).justify_content("space-between").align_items("stretch")
```

#### Supported values

- **`justify_content`**: `"start"`, `"center"`, `"end"`, `"space-between"`, `"space-around"`, `"space-evenly"`
- **`align_items`**: `"start"`, `"center"`, `"end"`, `"stretch"`

**Note**: Legacy value aliases (e.g., `"left"`, `"right"`, `"top"`, `"bottom"`) are not supported. Use standard CSS values.

---

### 3. Removal of `fill-available` Size Mode

The `'fill-available'` size mode has been removed in favor of the explicit `flex_grow()` method for CSS compliance.

**Before (v1.x):**
```python
Text("Flexible").size(width='fill-available')
Row(children).size(height='fill-available')
```

**After (v2.0):**
```python
Text("Flexible").flex_grow(1)
Row(children).flex_grow(1)
```

**Rationale**: In CSS, "filling available space" is a flex behavior (`flex-grow`), not a size value. This change makes the API more explicit and aligns with CSS Flexbox standards.

---

## Additional Methods

v2.0 introduces new positioning methods:

### `relative_position()`

Position an element relative to its normal flow position:
```python
Text("Nudged").relative_position(top=5, left=5)
```

### `place()`

Anchor-based positioning (replaces old `absolute_position(x, y)` behavior):
```python
Text("Overlay").place("center", "center")
```

### `translate()`

Apply post-layout transforms:
```python
Text("Centered")
    .absolute_position(top="50%", left="50%")
    .translate(x="-50%", y="-50%")
```

---

## Migration Checklist

- [ ] Replace `position(x, y, ...)` calls with `absolute_position(top=, left=, ...)` (parent-relative)
- [ ] Replace `absolute_position(x, y, ...)` calls with either:
  - `place(x, y, ...)` for anchor-based canvas positioning (recommended), or
  - `fixed_position(top=, left=, ...)` for CSS-style canvas positioning
- [ ] Rename layout methods:
  - `horizontal_distribution()` → `justify_content()`
  - `vertical_distribution()` → `justify_content()`
  - `vertical_align()` → `align_items()`
  - `horizontal_align()` → `align_items()`
- [ ] Replace `size(width='fill-available')` and `size(height='fill-available')` with `flex_grow(1)`
- [ ] Update alignment values to use CSS standard values (`"start"`, `"end"`, etc.)
- [ ] Run your test suite to verify layouts render correctly with the new engine

---

## New Features

For information about new features in v2.0 (such as `flex_grow`, `flex_shrink`, `aspect_ratio`, and size constraints), see the [CHANGELOG](CHANGELOG.md).

---

## Support

If you encounter issues during migration:
- Review the [CHANGELOG](CHANGELOG.md) for detailed version history
- Check existing [GitHub issues](https://github.com/francozanardi/pictex/issues)
- Open a new issue if you find a bug or need help