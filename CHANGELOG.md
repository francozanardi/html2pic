# Changelog

All notable changes to html2pic will be documented in this file.

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