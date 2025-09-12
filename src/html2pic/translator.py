"""
DOM to PicTex translation layer - converts styled DOM tree to PicTex builders
"""

from typing import Optional, Tuple, List, Union, Dict, Any
from pictex import *
from pictex import BorderStyle
from .models import DOMNode
from .exceptions import RenderError
from .warnings_system import get_warning_collector, WarningCategory

class PicTexTranslator:
    """
    Translates a styled DOM tree into PicTex builders.
    
    This is the heart of the HTML->PicTex conversion. It recursively walks
    the styled DOM tree and creates corresponding PicTex builders, applying
    all computed styles as method calls.
    
    The translation strategy:
    1. Determine the appropriate PicTex builder type based on HTML tag and CSS display
    2. Apply all styling properties as chained method calls
    3. Recursively process children and add them to containers
    """
    
    def __init__(self):
        self.warnings = get_warning_collector()
    
    def translate(self, styled_dom: DOMNode) -> Tuple[Canvas, Optional[Element]]:
        """
        Translate a styled DOM tree to PicTex builders.
        
        Args:
            styled_dom: Root DOM node with computed styles
            
        Returns:
            Tuple of (Canvas, root_element) where root_element may be None for empty docs
            
        Raises:
            RenderError: If translation fails
        """
        try:
            # Create base canvas
            canvas = Canvas()
            
            # Process children of the root node (skip the __root__ wrapper)
            if styled_dom.tag == "__root__" and styled_dom.children:
                # If there's only one child, return it directly
                if len(styled_dom.children) == 1:
                    root_element = self._translate_node(styled_dom.children[0])
                else:
                    # Multiple children, wrap in a Column
                    children_elements = []
                    for child in styled_dom.children:
                        element = self._translate_node(child)
                        if element is not None:
                            children_elements.append(element)
                    
                    if children_elements:
                        root_element = Column(*children_elements)
                    else:
                        root_element = None
            else:
                # Single root node
                root_element = self._translate_node(styled_dom)
            
            return canvas, root_element
            
        except Exception as e:
            raise RenderError(f"Failed to translate DOM to PicTex: {e}") from e
    
    def _translate_node(self, node: DOMNode) -> Optional[Element]:
        """
        Translate a single DOM node to a PicTex builder.
        
        Args:
            node: DOM node to translate
            
        Returns:
            PicTex Element or None if node should be skipped
        """
        if node.is_text():
            return self._create_text_element(node)
        elif node.is_element():
            return self._create_element_builder(node)
        else:
            return None
    
    def _create_text_element(self, node: DOMNode) -> Optional[Text]:
        """Create a PicTex Text element from a text node."""
        text_content = node.text_content.strip()
        if not text_content:
            return None
        
        # Create Text element
        text_element = Text(text_content)
        
        # Apply styles if the parent has computed styles
        if node.parent and node.parent.computed_styles:
            text_element = self._apply_text_styles(text_element, node.parent.computed_styles)
        
        return text_element
    
    def _create_element_builder(self, node: DOMNode) -> Optional[Element]:
        """
        Create a PicTex builder from an HTML element node.
        
        Strategy:
        1. Determine builder type based on tag and display property
        2. Create the builder
        3. Apply styling
        4. Add children
        """
        styles = node.computed_styles
        
        # Determine builder type
        builder = self._determine_builder_type(node)
        if builder is None:
            return None
        
        # Apply styling
        builder = self._apply_element_styles(builder, styles)
        
        # Add children for container elements
        if isinstance(builder, (Row, Column)):
            builder = self._add_children_to_container(builder, node)
        
        return builder
    
    def _determine_builder_type(self, node: DOMNode) -> Optional[Element]:
        """
        Determine which PicTex builder to use for an HTML element.
        
        Decision logic:
        1. <img> -> Image
        2. Elements with flex display -> Row/Column based on flex-direction
        3. Block elements -> Column (default vertical stacking)
        4. Inline elements -> Row (horizontal flow)
        5. Text-only elements -> wrap content in Text elements
        """
        tag = node.tag
        styles = node.computed_styles
        display = styles.get('display', 'block')
        
        # Handle img tags
        if tag == 'img':
            src = node.attributes.get('src')
            if src:
                try:
                    return Image(src)
                except Exception as e:
                    self.warnings.warn_element_skipped(
                        f"<img src='{src}'>", 
                        f"Failed to load image: {e}"
                    )
                    return None
            else:
                self.warnings.warn_element_skipped(
                    "<img>", 
                    "Missing src attribute"
                )
                return None  # Skip img without src
        
        # Handle flex containers
        if display == 'flex':
            flex_direction = styles.get('flex-direction', 'row')
            if flex_direction == 'column':
                return Column()
            else:
                return Row()
        
        # Handle text content - if element only contains text, make it a Text element
        if not node.children or all(child.is_text() for child in node.children):
            text_content = node.get_all_text().strip()
            if text_content:
                return Text(text_content)
            else:
                return Column()
        
        # Default container logic based on common HTML semantics
        block_tags = {'div', 'section', 'article', 'main', 'header', 'footer', 'aside', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        inline_tags = {'span', 'a', 'strong', 'em', 'b', 'i'}
        
        if tag in block_tags or display == 'block':
            return Column()  # Vertical stacking for block elements
        elif tag in inline_tags or display == 'inline':
            return Row()     # Horizontal flow for inline elements
        else:
            # Unknown element, default to Column
            return Column()
    
    def _apply_element_styles(self, builder: Element, styles: Dict[str, Any]) -> Element:
        """Apply computed CSS styles to a PicTex builder."""
        
        # Box model - size
        width = styles.get('width', 'auto')
        height = styles.get('height', 'auto')
        if width != 'auto' or height != 'auto':
            builder = self._apply_size(builder, width, height)
        
        # Box model - padding
        padding = self._get_box_values(styles, 'padding')
        if any(float(p.rstrip('px')) > 0 for p in padding if p.endswith('px')):
            if all(p == padding[0] for p in padding):
                # All sides equal
                builder = builder.padding(float(padding[0].rstrip('px')))
            elif padding[0] == padding[2] and padding[1] == padding[3]:
                # Vertical and horizontal
                builder = builder.padding(
                    float(padding[0].rstrip('px')), 
                    float(padding[1].rstrip('px'))
                )
            else:
                # All four sides
                builder = builder.padding(
                    float(padding[0].rstrip('px')), 
                    float(padding[1].rstrip('px')),
                    float(padding[2].rstrip('px')), 
                    float(padding[3].rstrip('px'))
                )
        
        # Box model - margin
        margin = self._get_box_values(styles, 'margin')
        if any(float(m.rstrip('px')) > 0 for m in margin if m.endswith('px')):
            if all(m == margin[0] for m in margin):
                builder = builder.margin(float(margin[0].rstrip('px')))
            elif margin[0] == margin[2] and margin[1] == margin[3]:
                builder = builder.margin(
                    float(margin[0].rstrip('px')),
                    float(margin[1].rstrip('px'))
                )
            else:
                builder = builder.margin(
                    float(margin[0].rstrip('px')),
                    float(margin[1].rstrip('px')),
                    float(margin[2].rstrip('px')),
                    float(margin[3].rstrip('px'))
                )
        
        # Background color
        bg_color = styles.get('background-color', 'transparent')
        if bg_color != 'transparent':
            builder = builder.background_color(bg_color)
        
        # Background image
        bg_image = styles.get('background-image', 'none')
        if bg_image != 'none' and bg_image:
            bg_size = styles.get('background-size', 'cover')
            builder = self._apply_background_image(builder, bg_image, bg_size)
        
        # Border
        border_width = styles.get('border-width', '0px')
        if border_width.endswith('px') and float(border_width[:-2]) > 0:
            border_color = styles.get('border-color', 'black')
            border_style = styles.get('border-style', 'solid')
            
            # Convert CSS border style to PicTex BorderStyle
            if border_style == 'dashed':
                pictex_style = BorderStyle.DASHED
            elif border_style == 'dotted':
                pictex_style = BorderStyle.DOTTED
            else:
                pictex_style = BorderStyle.SOLID
            
            builder = builder.border(
                float(border_width[:-2]),
                border_color,
                pictex_style
            )
        
        # Border radius
        border_radius = styles.get('border-radius', '0px')
        if border_radius.endswith('px') and float(border_radius[:-2]) > 0:
            builder = builder.border_radius(float(border_radius[:-2]))
        elif border_radius.endswith('%'):
            builder = builder.border_radius(border_radius)
        
        # Box shadows
        box_shadow = styles.get('box-shadow', 'none')
        if box_shadow != 'none':
            shadows = self._parse_box_shadows(box_shadow)
            if shadows:
                builder = builder.box_shadows(*shadows)
        
        # Layout properties for containers
        if isinstance(builder, (Row, Column)):
            builder = self._apply_layout_styles(builder, styles)
        
        # Typography (for Text elements or containers that might contain text)
        builder = self._apply_text_styles(builder, styles)
        
        # Positioning (absolute only)
        builder = self._apply_positioning(builder, styles)
        
        return builder
    
    def _apply_size(self, builder: Element, width: str, height: str) -> Element:
        """Apply width and height to a builder."""
        width_value = None
        height_value = None
        
        # Convert width
        if width != 'auto':
            if width.endswith('px'):
                width_value = float(width[:-2])
            elif width.endswith('%'):
                width_value = width
            elif width in ['fit-content', 'fill-available', 'fit-background-image']:
                width_value = width
        
        # Convert height
        if height != 'auto':
            if height.endswith('px'):
                height_value = float(height[:-2])
            elif height.endswith('%'):
                height_value = height
            elif height in ['fit-content', 'fill-available', 'fit-background-image']:
                height_value = height
        
        if width_value is not None or height_value is not None:
            return builder.size(width_value, height_value)
        
        return builder
    
    def _apply_layout_styles(self, builder: Union[Row, Column], styles: Dict[str, Any]) -> Union[Row, Column]:
        """Apply flexbox-like layout styles to Row/Column containers."""
        
        # Gap
        gap = styles.get('gap', '0px')
        if gap.endswith('px') and float(gap[:-2]) > 0:
            builder = builder.gap(float(gap[:-2]))
        
        # Flex properties
        if isinstance(builder, Row):
            # Horizontal distribution (main axis for Row)
            justify_content = styles.get('justify-content', 'flex-start')
            builder = self._apply_distribution(builder, justify_content, 'horizontal')
            
            # Vertical alignment (cross axis for Row)
            align_items = styles.get('align-items', 'stretch')
            builder = self._apply_alignment(builder, align_items, 'vertical')
            
        elif isinstance(builder, Column):
            # Vertical distribution (main axis for Column)
            justify_content = styles.get('justify-content', 'flex-start')
            builder = self._apply_distribution(builder, justify_content, 'vertical')
            
            # Horizontal alignment (cross axis for Column)
            align_items = styles.get('align-items', 'stretch')
            builder = self._apply_alignment(builder, align_items, 'horizontal')
        
        return builder
    
    def _apply_distribution(self, builder: Union[Row, Column], justify_value: str, axis: str) -> Union[Row, Column]:
        """Apply justify-content CSS property to PicTex distribution."""
        # Map CSS values to PicTex values
        distribution_map = {
            'flex-start': 'left' if axis == 'horizontal' else 'top',
            'center': 'center',
            'flex-end': 'right' if axis == 'horizontal' else 'bottom',
            'space-between': 'space-between',
            'space-around': 'space-around',
            'space-evenly': 'space-evenly'
        }
        
        pictex_value = distribution_map.get(justify_value, 'left' if axis == 'horizontal' else 'top')
        
        if axis == 'horizontal' and isinstance(builder, Row):
            return builder.horizontal_distribution(pictex_value)
        elif axis == 'vertical' and isinstance(builder, Column):
            return builder.vertical_distribution(pictex_value)
        
        return builder
    
    def _apply_alignment(self, builder: Union[Row, Column], align_value: str, axis: str) -> Union[Row, Column]:
        """Apply align-items CSS property to PicTex alignment."""
        # Map CSS values to PicTex values
        alignment_map = {
            'flex-start': 'left' if axis == 'horizontal' else 'top',
            'center': 'center',
            'flex-end': 'right' if axis == 'horizontal' else 'bottom',
            'stretch': 'stretch'
        }
        
        pictex_value = alignment_map.get(align_value, 'stretch')
        
        if axis == 'vertical' and isinstance(builder, Row):
            return builder.vertical_align(pictex_value)
        elif axis == 'horizontal' and isinstance(builder, Column):
            return builder.horizontal_align(pictex_value)
        
        return builder
    
    def _apply_text_styles(self, builder: Element, styles: Dict[str, Any]) -> Element:
        """Apply typography styles to a builder."""
        
        # Font family
        font_family = styles.get('font-family', '')
        if font_family and font_family != 'Arial, sans-serif':  # Skip default
            # Take first font from font stack
            first_font = font_family.split(',')[0].strip().strip('"\'')
            builder = builder.font_family(first_font)
        
        # Font size
        font_size = styles.get('font-size', '16px')
        if font_size.endswith('px'):
            builder = builder.font_size(float(font_size[:-2]))
        
        # Font weight
        font_weight = styles.get('font-weight', '400')
        if font_weight.isdigit():
            weight_num = int(font_weight)
            builder = builder.font_weight(weight_num)
        elif font_weight in ['bold', 'bolder']:
            builder = builder.font_weight(FontWeight.BOLD)
        
        # Font style
        font_style = styles.get('font-style', 'normal')
        if font_style == 'italic':
            builder = builder.font_style(FontStyle.ITALIC)
        
        # Text color
        color = styles.get('color', 'black')
        builder = builder.color(color)
        
        # Text align
        text_align = styles.get('text-align', 'left')
        if text_align == 'center':
            builder = builder.text_align(TextAlign.CENTER)
        elif text_align == 'right':
            builder = builder.text_align(TextAlign.RIGHT)
        
        # Line height
        line_height = styles.get('line-height', '1.2')
        try:
            lh_value = float(line_height)
            builder = builder.line_height(lh_value)
        except ValueError:
            pass  # Skip invalid line-height values
        
        # Text shadows
        text_shadow = styles.get('text-shadow', 'none')
        if text_shadow != 'none':
            shadows = self._parse_text_shadows(text_shadow)
            if shadows:
                builder = builder.text_shadows(*shadows)
        
        return builder
    
    def _apply_positioning(self, builder: Element, styles: Dict[str, Any]) -> Element:
        """Apply CSS positioning (absolute only) to a builder."""
        position = styles.get('position', 'static')
        
        if position == 'absolute':
            left = styles.get('left', 'auto')
            top = styles.get('top', 'auto')
            
            # Only apply positioning if left or top are specified
            if left != 'auto' or top != 'auto':
                x_pos = self._parse_position_value(left) if left != 'auto' else 0
                y_pos = self._parse_position_value(top) if top != 'auto' else 0
                
                # Use PicTex's absolute_position (which is actually relative to root canvas)
                builder = builder.absolute_position(x_pos, y_pos)
        elif position == 'relative':
            # Warn that relative positioning is not supported
            if any(styles.get(prop, 'auto') != 'auto' for prop in ['left', 'top', 'right', 'bottom']):
                self.warnings.warn_style_not_applied(
                    'position', 'relative', 'element', 
                    'Relative positioning is not supported. Use absolute positioning with left/top instead.'
                )
        elif position != 'static' and position != 'auto':
            # Warn about other unsupported position values
            self.warnings.warn_style_not_applied(
                'position', position, 'element',
                f"Position '{position}' is not supported. Only 'absolute' is supported."
            )
        
        return builder
    
    def _parse_position_value(self, value: str) -> Union[float, str]:
        """Parse CSS position value (left, top, etc.) to PicTex format."""
        if value == 'auto':
            return 0
        
        # Handle pixel values
        if value.endswith('px'):
            return float(value[:-2])
        
        # Handle percentage values
        if value.endswith('%'):
            return value  # PicTex supports percentage strings
        
        # Handle em/rem values (approximate)
        if value.endswith('em'):
            return float(value[:-2]) * 16
        if value.endswith('rem'):
            return float(value[:-3]) * 16
        
        # Try to parse as number
        try:
            return float(value)
        except ValueError:
            return 0
    
    def _add_children_to_container(self, container: Union[Row, Column], node: DOMNode) -> Union[Row, Column]:
        """Add child elements to a Row or Column container."""
        child_elements = []
        
        for child in node.children:
            child_element = self._translate_node(child)
            if child_element is not None:
                child_elements.append(child_element)
        
        # Create new container with children
        if isinstance(container, Row):
            new_container = Row(*child_elements)
        else:  # Column
            new_container = Column(*child_elements)
        
        # Copy over the styling from the original container
        new_container._style = container._style
        
        return new_container
    
    def _get_box_values(self, styles: Dict[str, Any], property_prefix: str) -> List[str]:
        """Get box model values (padding/margin) in [top, right, bottom, left] order."""
        top = styles.get(f'{property_prefix}-top', '0px')
        right = styles.get(f'{property_prefix}-right', '0px')
        bottom = styles.get(f'{property_prefix}-bottom', '0px')
        left = styles.get(f'{property_prefix}-left', '0px')
        
        return [top, right, bottom, left]
    
    def _parse_box_shadows(self, box_shadow_value: str) -> List[Shadow]:
        """
        Parse CSS box-shadow value into PicTex Shadow objects.
        
        Supports: offset-x offset-y blur-radius color
        Example: "2px 2px 4px rgba(0,0,0,0.5)"
        """
        shadows = []
        
        # Split multiple shadows by comma
        shadow_parts = box_shadow_value.split(',')
        
        for shadow_part in shadow_parts:
            shadow_part = shadow_part.strip()
            if shadow_part == 'none':
                continue
                
            try:
                shadow = self._parse_single_shadow(shadow_part)
                if shadow:
                    shadows.append(shadow)
            except Exception as e:
                self.warnings.warn_style_not_applied(
                    'box-shadow', shadow_part, 'element', f'Failed to parse shadow: {e}'
                )
        
        return shadows
    
    def _parse_text_shadows(self, text_shadow_value: str) -> List[Shadow]:
        """
        Parse CSS text-shadow value into PicTex Shadow objects.
        
        Same format as box-shadow: offset-x offset-y blur-radius color
        """
        return self._parse_box_shadows(text_shadow_value)  # Same parsing logic
    
    def _parse_single_shadow(self, shadow_str: str) -> Optional[Shadow]:
        """
        Parse a single shadow string into a Shadow object.
        
        Format: "offset-x offset-y blur-radius color"
        Example: "2px 2px 4px rgba(0,0,0,0.5)"
        """
        shadow_str = shadow_str.strip()
        
        # Smart parsing that doesn't break RGBA colors
        parts = []
        current_part = ""
        in_parentheses = 0
        
        for char in shadow_str + " ":  # Add space at end to trigger last part
            if char == "(":
                in_parentheses += 1
                current_part += char
            elif char == ")":
                in_parentheses -= 1
                current_part += char
            elif char.isspace() and in_parentheses == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
        
        if len(parts) < 3:
            return None
        
        try:
            # Parse offset values
            offset_x = self._parse_length_value(parts[0])
            offset_y = self._parse_length_value(parts[1])
            
            # Parse blur radius
            blur_radius = self._parse_length_value(parts[2])
            
            # Parse color (remaining parts)
            if len(parts) > 3:
                color_str = ' '.join(parts[3:])
            else:
                color_str = 'rgba(0,0,0,0.5)'  # Default shadow color
            
            # Convert color to SolidColor format
            if color_str.startswith('rgba(') or color_str.startswith('rgb('):
                # Parse RGBA to get proper color
                from .style_engine import StyleEngine
                style_engine = StyleEngine()
                normalized_color = style_engine._normalize_color(color_str)
                if normalized_color == 'transparent':
                    return None  # Skip transparent shadows
                color_str = normalized_color
            
            # Create PicTex Shadow object
            return Shadow(
                offset=(offset_x, offset_y),
                blur_radius=blur_radius,
                color=color_str
            )
            
        except Exception as e:
            return None
    
    def _parse_length_value(self, value_str: str) -> float:
        """Parse a CSS length value to pixels."""
        value_str = value_str.strip()
        
        if value_str.endswith('px'):
            return float(value_str[:-2])
        elif value_str.endswith('em'):
            # Approximate conversion (em to px)
            return float(value_str[:-2]) * 16
        elif value_str.endswith('rem'):
            return float(value_str[:-3]) * 16
        else:
            # Try to parse as number (assume pixels)
            return float(value_str)
    
    def _apply_background_image(self, builder: Element, bg_image: str, bg_size: str) -> Element:
        """
        Apply CSS background-image to a PicTex builder.
        
        Args:
            builder: PicTex element builder
            bg_image: CSS background-image value (url(...) or none)
            bg_size: CSS background-size value (cover, contain, or specific size)
            
        Returns:
            Builder with background image applied
        """
        try:
            # Check if it's a linear gradient
            if bg_image.startswith('linear-gradient('):
                # Parse CSS linear-gradient and convert to PicTex LinearGradient
                linear_gradient = self._parse_linear_gradient(bg_image)
                if linear_gradient:
                    # Use background_color() with gradient (PicTex accepts gradients here)
                    builder = builder.background_color(linear_gradient)
                return builder
            else:
                # Parse CSS background-image url() syntax
                image_path = self._parse_background_image_url(bg_image)
                if not image_path:
                    return builder
                
                # Map CSS background-size to PicTex size_mode
                size_mode = self._map_background_size(bg_size)
                
                # Apply background image
                builder = builder.background_image(image_path, size_mode=size_mode)
                
                return builder
            
        except Exception as e:
            self.warnings.warn_style_not_applied(
                'background-image', bg_image, 'element',
                f'Failed to apply background image: {e}'
            )
            return builder
    
    def _parse_background_image_url(self, bg_image: str) -> Optional[str]:
        """
        Parse CSS background-image url() value to extract the image path.
        
        Examples:
        - url("image.png") -> "image.png"
        - url('image.jpg') -> "image.jpg"
        - url(image.gif) -> "image.gif"
        - linear-gradient(...) -> None (not supported)
        """
        bg_image = bg_image.strip()
        
        # Check for url() function
        if bg_image.startswith('url(') and bg_image.endswith(')'):
            url_content = bg_image[4:-1].strip()  # Remove 'url(' and ')'
            
            # Remove quotes if present
            if (url_content.startswith('"') and url_content.endswith('"')) or \
               (url_content.startswith("'") and url_content.endswith("'")):
                url_content = url_content[1:-1]
            
            return url_content
        
        # Check for linear-gradient (now supported!)
        elif bg_image.startswith('linear-gradient('):
            return bg_image  # Return the gradient string for processing
        
        # Check for other unsupported gradient types
        elif bg_image.startswith(('radial-gradient', 'conic-gradient')):
            self.warnings.warn_style_not_applied(
                'background-image', bg_image, 'element',
                'Only linear-gradient is supported. Radial and conic gradients are not yet implemented.'
            )
            return None
        
        return None
    
    def _map_background_size(self, bg_size: str) -> str:
        """
        Map CSS background-size to PicTex size_mode.
        
        CSS background-size values:
        - cover: Scale image to cover entire container (may crop)
        - contain: Scale image to fit inside container (may leave empty space) 
        - auto: Use image's natural size (similar to tile)
        
        PicTex size_mode values:
        - cover: Scale to cover
        - contain: Scale to fit
        - tile: Repeat at natural size
        """
        bg_size = bg_size.strip().lower()
        
        if bg_size == 'cover':
            return 'cover'
        elif bg_size == 'contain':
            return 'contain'
        elif bg_size in ['auto', 'initial']:
            return 'tile'  # Use tile for natural size
        else:
            # For specific sizes like "100px 200px", we don't support it yet
            # Fall back to cover as a reasonable default
            if bg_size not in ['cover', 'contain', 'tile']:
                self.warnings.warn_style_not_applied(
                    'background-size', bg_size, 'element',
                    f'Specific background-size dimensions not supported. Using "cover" instead. Supported values: cover, contain, auto'
                )
            return 'cover'
    
    def _parse_linear_gradient(self, gradient_str: str) -> Optional[LinearGradient]:
        """
        Parse CSS linear-gradient() syntax and convert to PicTex LinearGradient.
        
        Supports:
        - linear-gradient(135deg, #667eea 0%, #764ba2 100%)
        - linear-gradient(to right, red, blue)
        - linear-gradient(45deg, red, yellow, blue)
        
        Args:
            gradient_str: CSS linear-gradient string
            
        Returns:
            LinearGradient object or None if parsing fails
        """
        try:
            # Remove 'linear-gradient(' and ')'
            if not gradient_str.startswith('linear-gradient(') or not gradient_str.endswith(')'):
                return None
            
            content = gradient_str[16:-1].strip()  # Remove 'linear-gradient(' and ')'
            
            # Split by comma, but be careful with nested parentheses (rgba colors)
            parts = self._smart_split_gradient(content)
            
            if not parts:
                return None
            
            # Parse direction (first part if it's a direction)
            direction = parts[0].strip()
            colors_start_index = 0
            
            start_point, end_point = self._parse_gradient_direction(direction)
            if start_point is not None:
                # First part was a direction, colors start from second part
                colors_start_index = 1
            else:
                # First part is a color, use default direction (left to right)
                start_point = (0.0, 0.0)
                end_point = (1.0, 0.0)
            
            # Parse colors and stops
            color_parts = parts[colors_start_index:]
            if len(color_parts) < 2:
                return None  # Need at least 2 colors
            
            colors = []
            stops = []
            
            for i, part in enumerate(color_parts):
                color, stop = self._parse_gradient_color_stop(part.strip())
                if color:
                    colors.append(color)
                    if stop is not None:
                        stops.append(stop)
                    else:
                        # Auto-distribute stops if not specified
                        if len(color_parts) == 2:
                            stops.append(0.0 if i == 0 else 1.0)
                        else:
                            stops.append(i / (len(color_parts) - 1))
            
            if len(colors) < 2:
                return None
            
            # Create PicTex LinearGradient
            return LinearGradient(
                colors=colors,
                stops=stops if len(stops) == len(colors) else None,
                start_point=start_point,
                end_point=end_point
            )
            
        except Exception as e:
            self.warnings.warn_style_not_applied(
                'background-image', gradient_str, 'element',
                f'Failed to parse linear-gradient: {e}'
            )
            return None
    
    def _smart_split_gradient(self, content: str) -> List[str]:
        """Split gradient content by comma, respecting parentheses"""
        parts = []
        current_part = ""
        paren_depth = 0
        
        for char in content:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
                continue
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def _parse_gradient_direction(self, direction: str) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """
        Parse CSS gradient direction and convert to start/end points.
        
        Returns (start_point, end_point) or (None, None) if not a direction
        """
        direction = direction.lower().strip()
        
        # Angle directions (e.g., 45deg, 135deg)
        if direction.endswith('deg'):
            try:
                angle = float(direction[:-3])
                # Convert angle to start/end points
                # CSS angles: 0deg = to top, 90deg = to right, 180deg = to bottom, 270deg = to left
                # We need to convert to start/end coordinates
                return self._angle_to_points(angle)
            except ValueError:
                return None, None
        
        # Keyword directions
        direction_map = {
            'to right': ((0.0, 0.0), (1.0, 0.0)),
            'to left': ((1.0, 0.0), (0.0, 0.0)),
            'to bottom': ((0.0, 0.0), (0.0, 1.0)),
            'to top': ((0.0, 1.0), (0.0, 0.0)),
            'to bottom right': ((0.0, 0.0), (1.0, 1.0)),
            'to bottom left': ((1.0, 0.0), (0.0, 1.0)),
            'to top right': ((0.0, 1.0), (1.0, 0.0)),
            'to top left': ((1.0, 1.0), (0.0, 0.0)),
        }
        
        if direction in direction_map:
            return direction_map[direction]
        
        return None, None
    
    def _angle_to_points(self, angle: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Convert CSS angle to start/end points"""
        import math
        
        # Normalize angle to 0-360 range
        angle = angle % 360
        
        # CSS gradient angles: 0deg = up, 90deg = right, 180deg = down, 270deg = left
        # Convert to radians and adjust for coordinate system
        rad = math.radians(angle - 90)  # -90 to align with CSS convention
        
        # Calculate end point on unit circle
        end_x = (math.cos(rad) + 1) / 2  # Convert from [-1,1] to [0,1]
        end_y = (math.sin(rad) + 1) / 2
        
        # Start point is opposite
        start_x = 1 - end_x
        start_y = 1 - end_y
        
        return (start_x, start_y), (end_x, end_y)
    
    def _parse_gradient_color_stop(self, part: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Parse a color stop like 'red 50%' or '#ff0000' or 'rgba(255,0,0,0.5) 25%'
        
        Returns (color, stop_position) where stop_position is 0.0-1.0 or None
        """
        part = part.strip()
        
        # Check if it has a percentage at the end
        if part.endswith('%'):
            # Find the last space before the percentage
            space_index = part.rfind(' ')
            if space_index > 0:
                color_part = part[:space_index].strip()
                percent_part = part[space_index + 1:].strip()
                try:
                    percent = float(percent_part[:-1])  # Remove '%'
                    return color_part, percent / 100.0
                except ValueError:
                    pass
        
        # No percentage, just return the color
        return part, None