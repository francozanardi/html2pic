"""Default CSS style values."""

DEFAULT_STYLES = {
    # Layout
    'display': 'block',
    'flex-direction': 'row',
    'justify-content': 'flex-start',
    'align-items': 'stretch',
    'gap': '0px',
    
    # Flex item properties
    'flex-grow': 'auto',
    'flex-shrink': 'auto',
    'align-self': 'auto',
    'flex-wrap': 'nowrap',
    
    # Box model - dimensions
    'width': 'auto',
    'height': 'auto',
    'min-width': 'auto',
    'max-width': 'none',
    'min-height': 'auto',
    'max-height': 'none',
    'aspect-ratio': 'auto',
    
    # Box model - spacing
    'padding-top': '0px',
    'padding-right': '0px',
    'padding-bottom': '0px',
    'padding-left': '0px',
    'margin-top': '0px',
    'margin-right': '0px',
    'margin-bottom': '0px',
    'margin-left': '0px',
    
    # Border
    'border-width': '0px',
    'border-style': 'solid',
    'border-color': 'black',
    'border-radius': '0px',
    'border-top-left-radius': '0px',
    'border-top-right-radius': '0px',
    'border-bottom-left-radius': '0px',
    'border-bottom-right-radius': '0px',
    
    # Visual
    'background-color': 'transparent',
    'background-image': 'none',
    'background-size': 'cover',
    'box-shadow': 'none',
    'text-shadow': 'none',
    
    # Typography
    'color': 'black',
    'font-family': '', # We leave this empty to use the pictex default font (Inter)
    'font-size': '16px',
    'font-weight': '400',
    'font-style': 'normal',
    'text-align': 'left',
    'line-height': '1.2',
    'text-decoration': 'none',
    'text-wrap': 'wrap',
    
    # Positioning
    'position': 'static',
    'top': 'auto',
    'right': 'auto',
    'bottom': 'auto',
    'left': 'auto',
    
    # Transforms
    'transform': 'none',
}
