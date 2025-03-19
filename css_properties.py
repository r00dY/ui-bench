from typing import Callable
import re
from colorsys import rgb_to_hsv
import math

NUMERIC_TOLERANCE = 0.25
COLOR_TOLERANCE = 0.25

# Helper functions
def extract_numeric_value(value: str) -> float:
    """Extract numeric value from CSS value string (e.g. '16px' -> 16.0)"""
    match = re.search(r'(\d+\.?\d*)', value)
    return float(match.group(1)) if match else 0.0

def parse_rgb(color: str) -> tuple[int, int, int]:
    """Parse RGB color string to tuple of integers"""
    match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color)
    if match:
        return tuple(int(x) for x in match.groups())
    return (0, 0, 0)

def parse_hex(color: str) -> tuple[int, int, int]:
    """Parse hex color to RGB tuple"""
    color = color.lstrip('#')
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

def color_distance(color1: str, color2: str) -> float:
    """Calculate perceptual color distance using HSV color space"""
    # Convert colors to RGB tuples
    rgb1 = parse_rgb(color1) if color1.startswith('rgb') else parse_hex(color1)
    rgb2 = parse_rgb(color2) if color2.startswith('rgb') else parse_hex(color2)
    
    # Convert to HSV
    hsv1 = rgb_to_hsv(*(x/255.0 for x in rgb1))
    hsv2 = rgb_to_hsv(*(x/255.0 for x in rgb2))
    
    # Calculate weighted differences
    h_diff = min(abs(hsv1[0] - hsv2[0]), 1 - abs(hsv1[0] - hsv2[0])) * 2
    s_diff = abs(hsv1[1] - hsv2[1])
    v_diff = abs(hsv1[2] - hsv2[2])
    
    return math.sqrt(h_diff**2 + s_diff**2 + v_diff**2)

def parse_aspect_ratio(ratio: str) -> float:
    """Convert aspect ratio string to float (e.g. '16/9' -> 1.777...)"""
    if '/' in ratio:
        num, den = map(float, ratio.split('/'))
        return num / den
    return float(ratio)

# Evaluator functions
def numeric_evaluator(reference: str, new: str, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    """Evaluate numeric values with percentage tolerance"""
    ref_val = extract_numeric_value(reference)
    new_val = extract_numeric_value(new)
    if ref_val == 0:
        return new_val == 0
    return abs(ref_val - new_val) / ref_val <= tolerance


def color_evaluator(reference: str, new: str, tolerance: float = COLOR_TOLERANCE) -> bool:
    """Evaluate colors with perceptual tolerance"""
    if reference == new:
        return True
    return color_distance(reference, new) <= tolerance

def aspect_ratio_evaluator(reference: str, new: str, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    """Evaluate aspect ratios with tolerance"""
    ref_ratio = parse_aspect_ratio(reference)
    new_ratio = parse_aspect_ratio(new)
    return abs(ref_ratio - new_ratio) / ref_ratio <= tolerance

def exact_match_evaluator(reference: str, new: str) -> bool:
    """Evaluate values that require exact matching"""
    return reference == new

def grid_template_evaluator(reference: str, new: str, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    """Evaluate grid-template-columns values with tolerance"""
    # Split into individual column values
    ref_cols = reference.strip().split()
    new_cols = new.strip().split()
    
    # Check if number of columns matches
    if len(ref_cols) != len(new_cols):
        return False
        
    # Compare each column value using numeric evaluator
    for ref_col, new_col in zip(ref_cols, new_cols):
        if not numeric_evaluator(ref_col, new_col, tolerance):
            return False
            
    return True


# Property evaluator mapping
css_properties: dict[str, Callable[[str, str], bool]] = {
    # Spacing properties - use numeric evaluator with 20% tolerance
    "margin-top": numeric_evaluator,
    "margin-bottom": numeric_evaluator,
    "margin-left": numeric_evaluator,
    "margin-right": numeric_evaluator,
    "padding-top": numeric_evaluator,
    "padding-bottom": numeric_evaluator,
    "padding-left": numeric_evaluator,
    "padding-right": numeric_evaluator,
    "top": numeric_evaluator,
    "left": numeric_evaluator,
    "bottom": numeric_evaluator,
    "right": numeric_evaluator,
    "width": numeric_evaluator,
    "height": numeric_evaluator,
    "max-width": numeric_evaluator,
    "max-height": numeric_evaluator,
    "min-width": numeric_evaluator,
    "min-height": numeric_evaluator,
    "gap": numeric_evaluator,

    # Layout properties - exact match required
    "display": exact_match_evaluator,
    "position": exact_match_evaluator,
    "flex-direction": exact_match_evaluator,
    "justify-content": exact_match_evaluator,
    "align-items": exact_match_evaluator,
    "grid-template-columns": grid_template_evaluator,
    "grid-template-rows": grid_template_evaluator,

    "grid-column-start": exact_match_evaluator,
    "grid-column-end": exact_match_evaluator,
    "grid-row-start": exact_match_evaluator,
    "grid-row-end": exact_match_evaluator,

    #border
    "border-top-width": numeric_evaluator,
    "border-bottom-width": numeric_evaluator,
    "border-left-width": numeric_evaluator,
    "border-right-width": numeric_evaluator,
    "border-top-style": exact_match_evaluator,
    "border-bottom-style": exact_match_evaluator,
    "border-left-style": exact_match_evaluator,
    "border-right-style": exact_match_evaluator,
    "border-top-color": color_evaluator,
    "border-bottom-color": color_evaluator,
    "border-left-color": color_evaluator,
    "border-right-color": color_evaluator,
    
    "border-radius": numeric_evaluator,
    "border-color": color_evaluator,
    "border-width": numeric_evaluator,
    "border-style": exact_match_evaluator,
    
    # Font properties - exact match required
    "font-family": exact_match_evaluator,
    "font-size": numeric_evaluator,
    "font-weight": exact_match_evaluator,
    "line-height": numeric_evaluator,
    "letter-spacing": exact_match_evaluator,
    "text-decoration-line": exact_match_evaluator,
    "text-align": exact_match_evaluator,
    "text-transform": exact_match_evaluator,

    # Color properties - use color evaluator
    "color": color_evaluator,
    "background-color": color_evaluator,
    "opacity": numeric_evaluator,

    # Other properties
    "object-fit": exact_match_evaluator,
    "aspect-ratio": aspect_ratio_evaluator,

    # Misc
    "backdrop-filter": None,
    "inset": None,
    "filter": None,
    "background": None,
    "all": None,
    "overflow": None,
}

