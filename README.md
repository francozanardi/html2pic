# html2pic

**Convert HTML + CSS to beautiful images using PicTex**

`html2pic` is a Python library that translates a subset of HTML and CSS to high-quality images without requiring a browser engine. Built on top of [PicTex](https://github.com/francozanardi/pictex), it provides a powerful and intuitive way to generate images from web markup.

## ⚠️ **Experimental Software Notice**

**This is experimental software developed primarily using AI assistance (Claude Code).** While functional, it should be used with caution in production environments. Key considerations:

- **Rapid Development**: Most of the codebase was generated and refined through AI-assisted programming
- **Limited Testing**: Extensive testing in diverse environments is still ongoing  
- **Active Development**: APIs and behavior may change significantly in future versions
- **Community Feedback Welcome**: Please report issues and suggest improvements via GitHub

Use this library for prototyping, experimentation, and non-critical applications. For production use, thorough testing is recommended.

## 🚀 Key Features

- **No Browser Required**: Pure Python implementation using PicTex as the rendering engine
- **Flexbox Support**: Modern CSS layout with `display: flex`, `justify-content`, `align-items`, etc.
- **Rich Typography**: Font families, sizes, weights, colors, text decorations, and @font-face support
- **Box Model**: Complete support for padding, margins, borders, and border-radius  
- **Responsive Sizing**: Supports px, em, rem, % units and flexible sizing modes
- **High Quality Output**: Vector (SVG) and raster (PNG, JPG) output formats
- **Simple API**: Clean, intuitive interface inspired by modern web development

## 📦 Installation

```bash
pip install html2pic
```

## 🎯 Quick Start

```python
from html2pic import Html2Pic

# Your HTML content
html = '''
<div class="card">
    <h1>Hello, World!</h1>
    <p class="subtitle">Generated with html2pic</p>
</div>
'''

# Your CSS styles
css = '''
.card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    background-color: #f0f8ff;
    border-radius: 15px;
    width: 300px;
}

h1 {
    color: #2c3e50;
    font-size: 28px;
    margin: 0 0 10px 0;
}

.subtitle {
    color: #7f8c8d;
    font-size: 16px;
    margin: 0;
}
'''

# Create and render
renderer = Html2Pic(html, css)
image = renderer.render()
image.save("output.png")
```

## 🏗️ Architecture

html2pic works by translating HTML + CSS concepts to PicTex builders:

1. **HTML Parser**: Uses BeautifulSoup to create a DOM tree
2. **CSS Parser**: Uses tinycss2 to extract style rules  
3. **Style Engine**: Applies CSS cascade, specificity, and inheritance
4. **Translator**: Maps styled DOM nodes to PicTex builders (Canvas, Row, Column, Text, Image)
5. **Renderer**: Uses PicTex to generate the final image

## 📋 Supported HTML/CSS Features

### HTML Elements
- `<div>`, `<section>`, `<article>` → Layout containers
- `<h1>`-`<h6>`, `<p>`, `<span>` → Text elements
- `<img>` → Image elements

### CSS Layout
- `display: flex` with `flex-direction: row|column`
- `display: none` for hiding elements completely
- `justify-content`: `flex-start`, `center`, `flex-end`, `space-between`, `space-around`, `space-evenly`
- `align-items`: `flex-start`, `center`, `flex-end`, `stretch`
- `gap` for spacing between flex items

### CSS Box Model
- `width`, `height` (px, %, auto, fit-content, fill-available)
- `padding`, `margin` (shorthand and individual sides)
- `border` with width, style (solid, dashed, dotted), and color
- `border-radius` (px and %) with full individual corner support
  - Individual properties: `border-top-left-radius`, `border-top-right-radius`, `border-bottom-left-radius`, `border-bottom-right-radius`
- `background-color` (solid colors, linear gradients, and RGBA with alpha channel)
- `background-image` (url() and linear-gradient())
- `background-size` (cover, contain, tile for images)
- `box-shadow` (offset-x, offset-y, blur-radius, color with RGBA support)

### CSS Typography
- `font-family`, `font-size`, `font-weight`, `font-style`
- `color`, `text-align`, `line-height`
- `text-decoration` (underline, line-through)
- `text-shadow` (offset-x, offset-y, blur-radius, color)
- `@font-face` declarations with full weight and style matching

#### Font Loading

html2pic supports multiple ways to load custom fonts with proper fallback support:

**@font-face Support (Recommended)**
```css
/* Define custom fonts with @font-face */
@font-face {
    font-family: "MyCustomFont";
    src: url("./fonts/custom-font.ttf");
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: "MyCustomFont";
    src: url("./fonts/custom-font-bold.ttf");
    font-weight: bold;
    font-style: normal;
}

/* Use with fallbacks */
h1 {
    font-family: "MyCustomFont", Arial, sans-serif;
    font-weight: bold;
}
```

**Direct Font File References**
```css
/* System font */
font-family: "Arial", sans-serif;

/* Custom font file (provide absolute or relative path) */
font-family: "/path/to/custom-font.ttf";

/* Multiple fallbacks */
font-family: "Custom Font", "Arial", sans-serif;
```

**Features:**
- **@font-face declarations**: Full CSS @font-face support with font-family, src, font-weight, and font-style
- **Font fallbacks**: Automatic fallback chain resolution - @font-face fonts are prioritized, then system fonts. **Font fallbacks are only used for not supported glyphs in the previous font, but the provided fonts must exist**. 
- **Weight and style matching**: Different font files for different weights (normal, bold) and styles (normal, italic)
- **Flexible paths**: Support for relative paths, absolute paths, and URLs in src property
- **PicTex integration**: Uses PicTex's `font_fallbacks()` function for optimal font rendering

**Note**: When using @font-face, provide paths to font files (.ttf, .otf, .woff2). If a font cannot be loaded, the system automatically falls back to the next font in the fallback chain.

#### Linear Gradients
html2pic supports CSS linear-gradient syntax for backgrounds:

```css
/* Angle-based gradients */
background-image: linear-gradient(135deg, #667eea, #764ba2);

/* Direction keywords */  
background-image: linear-gradient(to right, red, blue);

/* Color stops with percentages */
background-image: linear-gradient(90deg, #ff0000 0%, #00ff00 50%, #0000ff 100%);

/* Multiple colors */
background-image: linear-gradient(45deg, yellow, orange, red, purple);
```

**Supported features:**
- Angle directions (0deg, 45deg, 135deg, etc.)
- Keyword directions (to right, to bottom, to top left, etc.)  
- Color stops with percentages
- Multiple colors with automatic distribution
- All CSS color formats (hex, rgb, rgba, named colors)

**Limitations**: Only linear gradients are supported. Radial and conic gradients are not yet implemented.

### CSS Positioning
- `position: absolute` with `left` and `top` properties (px, %, em, rem)
- **Limitation**: Only `left` and `top` are supported, not `right` or `bottom`

### CSS At-Rules
- `@font-face` declarations for custom font loading

### CSS Selectors
- Tag selectors: `div`, `p`, `h1`
- Class selectors: `.my-class`
- ID selectors: `#my-id`
- Universal selector: `*`

## 📝 Examples

Explore the `examples/` folder for complete runnable examples with generated output images.

### Quick Start Example
Basic card layout demonstrating core html2pic functionality:

```python
from html2pic import Html2Pic

html = '''
<div class="card">
    <h1>Hello, World!</h1>
    <p class="subtitle">Generated with html2pic</p>
</div>
'''

css = '''
.card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    background-color: #f0f8ff;
    border-radius: 15px;
    width: 300px;
}

h1 {
    color: #2c3e50;
    font-size: 28px;
    margin: 0 0 10px 0;
}

.subtitle {
    color: #7f8c8d;
    font-size: 16px;
    margin: 0;
}
'''

renderer = Html2Pic(html, css)
image = renderer.render()
image.save("output.png")
```

![Quick Start Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/01_quick_start_output.png)

### Individual Border-Radius Properties
Showcase different corner radius values:

```python
html = '''
<div class="card-container">
    <div class="rounded-card">Individual Corner Radii</div>
</div>
'''

css = '''
.card-container {
    padding: 20px;
    background-color: #f5f5f5;
}

.rounded-card {
    width: 300px;
    height: 150px;
    background-color: #e1f5fe;
    padding: 20px;
    border: 3px solid #0277bd;

    /* Individual corner border-radius properties */
    border-top-left-radius: 5px;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 40px;
    border-bottom-left-radius: 10px;

    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: #01579b;
}
'''

renderer = Html2Pic(html, css)
image = renderer.render()
image.save("border_radius_example.png")
```

![Individual Border-Radius Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/border_radius_example.png)

### Alpha Channel Colors and Display None
Advanced styling with transparency and hidden elements:

```python
html = '''
<div class="container">
    <div class="visible-card">Visible Card</div>
    <div class="hidden-card">This won't appear</div>
    <div class="transparent-card">Semi-transparent Card</div>
</div>
'''

css = '''
.container {
    display: flex;
    flex-direction: column;
    gap: 15px;
    padding: 20px;
}

.visible-card {
    background-color: rgba(76, 175, 80, 0.9);
    padding: 15px;
    border-radius: 8px;
    color: white;
}

.hidden-card {
    background-color: red;
    padding: 15px;
    display: none; /* This element won't be rendered at all */
}

.transparent-card {
    background-color: rgba(33, 150, 243, 0.3); /* Semi-transparent blue */
    padding: 15px;
    border-radius: 8px;
    border: 2px solid rgba(33, 150, 243, 0.8);
}
'''

renderer = Html2Pic(html, css)
image = renderer.render()
image.save("advanced_styling_example.png")
```

![Advanced Styling Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/advanced_styling_example.png)

### Flexbox Card Layout
Social media style user card with horizontal layout:

```python
html = '''
<div class="user-card">
    <div class="avatar"></div>
    <div class="user-info">
        <h2>Alex Doe</h2>
        <p>@alexdoe</p>
    </div>
</div>
'''

css = '''
.user-card {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 20px;
    background-color: white;
    border-radius: 12px;
    border: 1px solid #e1e8ed;
}

.avatar {
    width: 60px;
    height: 60px;
    background-color: #1da1f2;
    border-radius: 50%;
}

.user-info h2 {
    margin: 0 0 4px 0;
    font-size: 18px;
    color: #14171a;
}

.user-info p {
    margin: 0;
    color: #657786;
    font-size: 14px;
}
'''
```

![Flexbox Card Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/02_flexbox_card_output.png)

### Advanced Visual Effects
Shadows, positioning, and advanced styling features:

![Shadows and Effects Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/04_shadows_and_effects_output.png)

### Background Images  
Background image support with different sizing modes:

![Background Images Result](https://raw.githubusercontent.com/francozanardi/html2pic/main/examples/05_background_images_output.png)

**Complete examples** with full source code are available in the [`examples/`](examples/) directory.

## 🔧 API Reference

### Html2Pic Class

```python
Html2Pic(html: str, css: str = "", base_font_size: int = 16)
```

**Methods:**
- `render(crop_mode=CropMode.SMART) -> BitmapImage`: Render to raster image
- `render_as_svg(embed_font=True) -> VectorImage`: Render to SVG
- `debug_info() -> dict`: Get debugging information about parsing and styling

### Output Objects

The rendered images are PicTex `BitmapImage` or `VectorImage` objects with methods like:
- `save(filename)`: Save to file
- `to_numpy()`: Convert to NumPy array  
- `to_pillow()`: Convert to PIL Image
- `show()`: Display the image

## 🚧 Current Limitations  

This is an early version focusing on core functionality. A lot of features are not yet supported.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on top of [PicTex](https://github.com/francozanardi/pictex) for high-quality rendering
- Uses [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing  
- Uses [tinycss2](https://github.com/Kozea/tinycss2) for CSS parsing
