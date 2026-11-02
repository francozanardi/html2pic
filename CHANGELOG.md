# Changelog

All notable changes to html2pic will be documented in this file.

## [Unreleased]

### Added
- `<style>` elements and `style=""` attributes are applied (#1).
- `base_url` argument: relative URLs of images, fonts and stylesheets resolve against it (or
  against `<base href>`); `url()`s inside a stylesheet resolve against that stylesheet (#3).
- `fetcher` argument to opt into loading `<link rel="stylesheet">`, `@import` and remote
  images/fonts, plus ready-made `local_fetcher`, `http_fetcher` and `chain_fetchers` in
  `html2pic.fetchers`. Nothing is fetched without it.
- `data:` URIs for images, fonts and stylesheets.
- `radial-gradient()`, `conic-gradient()` and `repeating-linear/radial/conic-gradient()` (#5).
- `overflow`, `overflow-x` and `overflow-y` (clipping) (#5).
- Descendant (`.card h1`), child (`ul > li`) and compound (`div.card#main`) selectors, with
  real CSS specificity. Still-unsupported selectors are skipped with a warning.
- `background` shorthand (color and/or `url()`/`linear-gradient()` image).
- `hsl()`/`hsla()` colors and modern `rgb()` syntax (`rgb(255 0 0 / 50%)`, percentage channels).
- `text-decoration: underline | line-through`.
- Test suite (unit + rendering integration tests) and GitHub Actions CI on Python 3.9–3.13.

### Fixed
- Linear gradients now use the exact CSS geometry: the gradient line length depends on the
  box's aspect ratio, corner directions (`to top right`) are perpendicular to the diagonal,
  px stop positions and stops outside 0–100% work, and colors interpolate in premultiplied
  space. A `background-color` is now painted underneath a gradient instead of being replaced.
- `@media` blocks were parsed as regular rules with a bogus selector; they are now skipped
  with a warning.
- Remote `@font-face` URLs were documented as supported but silently ignored.
- `rem` units were never converted.
- `font-size` in `em`/`%` was relative to 16px instead of the parent's font size.
- Percentage `border-radius` (e.g. `50%` for circles) and other percentage values were
  computed against the parent's value of the same property and usually became `0`.
- `line-height` in `px` was used as a font-size multiplier (`24px` → 24× the font size).
- User rules such as `div { ... }` or `* { ... }` were also applied to the internal root
  wrapper, adding extra padding/margins/backgrounds around the output.
- `rgb()`/`rgba()` color stops in `linear-gradient()` were dropped.
- Debug output was printed to stdout for every element with a `transform`.

### Changed
- `requires-python` raised to `>=3.9` (required by PicTex 2.x).
- Percentage `padding`, `margin` and `gap` now emit a warning instead of being dropped silently.

## [0.2.2] - 2026-01-28

### Fixed
- Typo in import

## [0.2.0] - 2026-01-10

### ⚠️ BREAKING CHANGES

This release requires **PicTex 2.0** or higher. The underlying layout engine has been migrated to use Taffy (via `stretchable` bindings).

- **`fill-available` size mode removed**: This was a non-standard CSS value internal to PicTex 1.x. Use `flex-grow: 1` in your CSS instead for elements that should fill available space.

### ✨ New Features

- **Full CSS Positioning Support**: Complete implementation of CSS positioning model
  - `position: relative` with `top`, `right`, `bottom`, `left` offsets
  - `position: absolute` for parent-relative positioning  
  - `position: fixed` for canvas-relative positioning
  - All four inset properties (`top`, `right`, `bottom`, `left`) now supported

- **Flex Item Properties**: Fine-grained flexbox control
  - `flex-grow`: Control how elements grow to fill available space
  - `flex-shrink`: Control how elements shrink when space is limited  
  - `align-self`: Override container's alignment for individual items

- **Multi-line Flex Containers**: 
  - `flex-wrap: wrap` and `flex-wrap: wrap-reverse` for responsive layouts

- **Size Constraints**:
  - `min-width`, `max-width`: Set width boundaries
  - `min-height`, `max-height`: Set height boundaries
  - All support both pixel and percentage values

- **Aspect Ratio**:
  - `aspect-ratio`: Maintain element proportions (e.g., `16/9` or `1.777`)

- **CSS Transforms (translate only)**:
  - `transform: translate(x, y)`, `translateX(x)`, `translateY(y)`
  - Enables anchor-based centering: `top: 50%; left: 50%; transform: translate(-50%, -50%)`

- **CSS-Standard Values**: Now accepts both CSS standard values (`start`, `end`) and flex-prefixed values (`flex-start`, `flex-end`) for `justify-content` and `align-items`

### 🔧 Improvements

- **Robust Layout Engine**: Migrated to Taffy-based layout engine via PicTex 2.0 for improved flexbox correctness
- **Better Text Wrapping**: Improved text wrapping behavior in nested containers
- **Percentage-based Sizing**: More accurate percentage-based width/height calculations

### 🏗️ Internal Changes

- Translator updated to use PicTex 2.0 API:
  - `justify_content()` replaces `horizontal_distribution()`/`vertical_distribution()`
  - `align_items()` replaces `vertical_align()`/`horizontal_align()`
  - Positioning uses keyword arguments (`top=`, `left=`, etc.) instead of positional args
- Added new helper methods for size constraints, aspect ratio, and flex item properties
- Updated CSS validation to recognize new properties

## [0.1.3] - 2024-09-13

### ✨ New Features
- **Individual Border-Radius Properties**: Full support for individual corner border-radius properties
  - `border-top-left-radius`, `border-top-right-radius`, `border-bottom-left-radius`, `border-bottom-right-radius`
  - Works alongside existing shorthand `border-radius` property
  - Support for both px and percentage values for each corner
  - Proper priority handling: individual properties override shorthand when specified

- **Alpha Channel Color Support**: Enhanced color handling with full alpha channel support
  - RGBA colors now properly rendered with transparency
  - Alpha values below 0.01 automatically converted to 'transparent'
  - Improved color validation and normalization
  - Full hex RGBA support (#rrggbbaa format)

- **Display None Support**: Complete CSS `display: none` implementation
  - Elements with `display: none` are completely omitted from rendering
  - Children of hidden elements are also properly excluded
  - Zero performance impact for hidden elements (not rendered at all)
  - Semantically correct behavior matching standard CSS

### 🔧 Improvements
- Enhanced CSS parser to recognize and validate individual border-radius properties
- Updated translator to use PicTex's native 4-corner border-radius API
- Improved color parsing system with better error handling and transparency support
- Optimized element generation to skip hidden elements entirely

### 🏗️ Architecture Changes
- Extended CSS property validation lists to include individual border-radius properties
- Modified translator's `_get_border_radius_values()` to return proper PicTex format
- Updated style engine's `_normalize_display()` to handle 'none' value
- Added early return logic in `_create_element_builder()` for display: none elements

## [0.1.2] - 2024-09-13

### ✨ New Features
- **@font-face Support**: Full CSS @font-face declarations with advanced font loading
  - Complete @font-face parsing with `font-family`, `src`, `font-weight`, and `font-style` properties
  - Support for multiple font weights and styles (normal, bold, italic) per font family
  - Flexible font source paths: relative paths, absolute paths, and URLs

### 🔧 Improvements
- Enhanced CSS parser to detect and process @font-face at-rules separately from regular CSS rules
- Added FontRegistry system for managing and resolving font declarations
- Updated font resolution logic to match fonts by weight and style specifications
- Improved typography system to use advanced font fallback chains instead of single font selection

### 🏗️ Architecture Changes
- Added `FontFace` and `FontRegistry` classes to `models.py`
- Extended CSS parser with @font-face specific parsing methods
- Updated style engine and translator to integrate font registry throughout the rendering pipeline
- Modified core `Html2Pic` class to expose font registry in debug information

## [0.1.1] - 2024-09-12

### ✨ New Features
- **Linear Gradient Support**: Added full support for CSS `linear-gradient()` in backgrounds
  - Angle-based gradients: `linear-gradient(135deg, #667eea, #764ba2)`
  - Keyword directions: `linear-gradient(to right, red, blue)`
  - Color stops with percentages: `linear-gradient(90deg, red 0%, blue 100%)`
  - Multiple colors with automatic distribution
  - Support for all CSS color formats (hex, rgb, rgba, named colors)

### 🔧 Improvements
- Updated documentation with linear-gradient examples and limitations
- Enhanced background rendering system to handle both images and gradients
- Improved CSS parser to recognize linear-gradient as supported feature

### 📝 Documentation
- Added comprehensive linear-gradient documentation to README
- Updated examples to showcase gradient capabilities
- Clarified that only linear gradients are supported (radial/conic not yet implemented)

## [0.1.0] - 2024-09-12

### Initial Release

#### ✨ Core Features
- **HTML to Image Conversion**: Convert HTML + CSS to high-quality images using PicTex as rendering engine
- **Modern CSS Layout**: Full flexbox support with `display: flex`, `justify-content`, `align-items`, `gap`, etc.
- **Rich Typography**: Font families, sizes, weights, colors, text decorations, text shadows
- **Complete Box Model**: Padding, margins, borders, border-radius support
- **Visual Effects**: Box shadows and text shadows with RGBA color support
- **Positioning**: Absolute positioning with `left` and `top` properties
- **Background Images & Gradients**: Support for `background-image` with `url()` syntax and `linear-gradient()`, plus `background-size` (cover, contain, tile)

#### 🏗️ Architecture
- **Modular Design**: Clean separation of HTML parser, CSS parser, style engine, and translator
- **Comprehensive Warnings System**: Detailed debugging information for unsupported features
- **CSS Cascade Engine**: Proper specificity calculations and inheritance
- **Smart Translation**: Maps HTML/CSS concepts to PicTex builders (Canvas, Row, Column, Text, Image)

#### 📋 Supported HTML Elements
- Container elements: `div`, `section`, `article`, `header`, `footer`, `main`, `nav`, `aside`
- Text elements: `h1`-`h6`, `p`, `span`, `strong`, `em`, `b`, `i`, `u`, `s`
- Media elements: `img`
- List elements: `ul`, `ol`, `li`
- Other: `a`, `br`, `hr`

#### 🎨 Supported CSS Features
- **Layout**: `display` (flex, block, inline), `flex-direction`, `justify-content`, `align-items`, `gap`
- **Box Model**: `width`, `height`, `padding`, `margin`, `border`, `border-radius`
- **Typography**: `font-family`, `font-size`, `font-weight`, `font-style`, `color`, `text-align`, `line-height`, `text-decoration`
- **Visual Effects**: `background-color`, `background-image`, `background-size`, `box-shadow`, `text-shadow`
- **Positioning**: `position: absolute` with `left` and `top`
- **Units**: `px`, `em`, `rem`, `%` support
- **Colors**: Hex, RGB, RGBA, and named colors

#### 🚨 Intelligent Warnings System
- **CSS Validation**: Warns about unexpected/invalid CSS property values
- **HTML Element Detection**: Warns about unrecognized or unsupported HTML elements
- **Feature Limitations**: Clear warnings about unsupported CSS features with alternatives
- **Color Fallbacks**: Automatic fallback for invalid colors with warnings
- **Categorized Warnings**: Organized by HTML parsing, CSS parsing, style application, etc.

#### 🔧 Developer Experience
- **Simple API**: Clean `Html2Pic(html, css).render()` interface
- **Multiple Output Formats**: PNG, JPG via PicTex integration
- **Debug Information**: `get_warnings()`, `print_warnings()`, `get_warnings_summary()` methods
- **Error Handling**: Graceful degradation with informative warnings instead of crashes

#### 🏃‍♂️ Performance Features
- **Empty Element Optimization**: Only renders elements with visual styles
- **Smart RGBA Parsing**: Proper handling of RGBA colors in shadows and backgrounds
- **Efficient Shadow Parsing**: Supports multiple shadows on single elements

#### 🌟 Special Improvements
- **Fixed Empty Div Rendering**: Empty divs with visual styles (background, borders, shadows) now render correctly
- **Advanced Shadow Support**: Full CSS shadow syntax with multiple shadows and RGBA colors
- **Background Image Integration**: Complete CSS background-image support with PicTex backend
- **Comprehensive Property Validation**: Validates CSS values and provides helpful error messages

### Known Limitations
- CSS Grid layout not supported (use Flexbox instead)
- Relative positioning not supported (use absolute positioning)
- CSS transforms and animations not supported
- Background gradients not supported (use solid colors or images)
- Complex selectors (descendants, pseudo-classes) not supported

### Dependencies
- PicTex: High-quality rendering engine
- BeautifulSoup4: HTML parsing
- tinycss2: CSS parsing

---

*This project was developed using AI assistance (Claude Code) for rapid prototyping and implementation.*