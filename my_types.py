from typing import Dict, List, Optional
from pydantic import BaseModel, model_validator
from css_properties import css_properties

StyleSheet = Dict[str, Dict[str, str]]



class Variant(BaseModel):
    id: str
    css_changes: StyleSheet

class Config(BaseModel):
    correct_css: StyleSheet
    test__corrected_css: Optional[StyleSheet] = None
    
    variants: List[Variant] = []

    def get_variant(self, id: str) -> Optional[Variant]:
        if self.variants:
            for variant in self.variants:
                if variant.id == id:
                    return variant
        return None

    @model_validator(mode="after")
    def validate(self):
        # Validate that all CSS properties in correct_css are allowed
        for selector, properties in self.correct_css.items():
            for prop_name in properties.keys():
                if prop_name not in css_properties.keys():
                    raise ValueError(f"Invalid CSS property '{prop_name}' in correct_css")
        
        for variant in self.variants:
            self.verify_css_changes(variant.css_changes)
                
        return self

    def verify_css_changes(self, css_changes: StyleSheet) -> bool:

        wrong_selectors = []
        non_existing_properties = []
        not_allowed_properties = []
        properties_without_evaluator = []

        # Check each selector in css_changes exists in correct_css
        for selector, properties in css_changes.items():
            if selector not in self.correct_css:
                wrong_selectors.append(selector)
                continue
            
            # Check each property exists in correct_css for this selector
            existing_properties = self.correct_css[selector]
            for prop_name in properties.keys():
                if prop_name not in existing_properties:
                    non_existing_properties.append((selector, prop_name))
                    continue
                
                # Verify property is allowed and has an evaluator
                if prop_name not in css_properties:
                    not_allowed_properties.append((selector, prop_name))
                    continue

                if css_properties[prop_name] is None:
                    properties_without_evaluator.append((selector, prop_name))
                    continue
        
        # If all error arrays are empty, return True (no errors)
        if not wrong_selectors and not non_existing_properties and not not_allowed_properties and not properties_without_evaluator:
            return
        
        # Otherwise, construct error message with all detected errors
        error_message = "CSS changes validation failed:"
        
        if wrong_selectors:
            selectors_str = ", ".join(wrong_selectors)
            error_message += f"\n- Invalid selectors: {selectors_str}"
            
        if non_existing_properties:
            props_str = ", ".join([f"{s} -> {p}" for s, p in non_existing_properties])
            error_message += f"\n- Properties not in correct_css: {props_str}"
            
        if not_allowed_properties:
            props_str = ", ".join([f"{s} -> {p}" for s, p in not_allowed_properties])
            error_message += f"\n- Properties not allowed: {props_str}"
            
        if properties_without_evaluator:
            props_str = ", ".join([f"{s} -> {p}" for s, p in properties_without_evaluator])
            error_message += f"\n- Properties without evaluator: {props_str}"
            
        raise ValueError(error_message)


    model_config = {
        'error_mode': 'verbose'
    }


# # space scale: 1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160


# # space scale: 0px, 1px, 2px, 4px, 6px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px, 128px, 160px



# space_scale = [
#     "0px",
#     "1px",
#     "2px",
#     "4px", 
#     "6px",
#     "8px",
#     "12px",
#     "16px",
#     "24px",
#     "32px",
#     "48px",
#     "64px",
#     "96px",
#     "128px",
#     "160px"
# ]


# allowed_css_properties = [
#     "margin-top",
#     "margin-bottom",
#     "margin-left",
#     "margin-right",
#     "padding-top",
#     "padding-bottom",
#     "padding-left",
#     "padding-right",
#     "top",
#     "left",
#     "bottom",
#     "right",
#     "width",
#     "height",

#     "max-width",
#     "gap",

#     "display",
#     "position",

#     "flex-direction",
#     "justify-content",
#     "align-items",
#     "grid-template-columns",

#     #fonts
#     "font-family",
#     "font-size",
#     "font-weight",
#     "letter-spacing",
#     "text-decoration-style",

#     #colors
#     "color",
#     "background-color", 

#     #others
#     "object-fit",
#     "aspect-ratio",
# ]


# # Important comment
# # 
# # - Do we need to add all those scales actually? 
# # - When we create erronous variant, and specify clearly the number of errors, can't we just render and see whether those properties are correct? 
# # - 
# # 
# # Errors we want to introduce:
# # - spacings (padding, margin, gap, width, height etc)
# # - container size, padding (max width actually)
# # - font sizes, families, weights (not necessarily letter spacings right now)
# # - font decoration
# # - colors (for fonts, SVGs and backgrounds)
# # - object fit
# # - aspect ratio
# # - layout (grid, flex properties)
# #
# # TODO:
# # - for each property we want to modify we must have "evaluation strategy first". WE must have simply EVALUATOR FUNCTION. 2 values and "are they equal?". Comparators! Evaluators.
# # - only later we can add design system to the prompt


# allowed_css_properties_new = {
#     # Spacing properties
#     "margin-top": space_scale,
#     "margin-bottom": space_scale,
#     "margin-left": space_scale,
#     "margin-right": space_scale,
#     "padding-top": space_scale,
#     "padding-bottom": space_scale,
#     "padding-left": space_scale,
#     "padding-right": space_scale,
#     "top": space_scale,
#     "left": space_scale,
#     "bottom": space_scale,
#     "right": space_scale,
#     "width": space_scale + ["auto", "100%"],
#     "height": space_scale + ["auto", "100%"],
#     "max-width": space_scale + ["100%"],
#     "gap": space_scale,

#     # Layout properties
#     "display": ["flex", "grid", "block", "inline-block", "inline", "none"],
#     "position": ["static", "relative", "absolute", "fixed", "sticky"],
#     "flex-direction": ["row", "row-reverse", "column", "column-reverse"],
#     "justify-content": ["flex-start", "flex-end", "center", "space-between", "space-around", "space-evenly"],
#     "align-items": ["flex-start", "flex-end", "center", "baseline", "stretch"],
#     "grid-template-columns": ["1fr 1fr 1fr 1fr", "repeat(4, 1fr)"],

#     # Font properties
#     "font-family": ["'PANGAIA', sans-serif"],
#     "font-size": ["10px", "12px", "14px", "16px", "20px", "24px", "28px", "32px"],
#     "font-weight": ["300", "400", "500", "600", "700"],
#     "letter-spacing": ["normal", "0.05em", "-0.05em"],
#     "text-decoration": ["none", "underline"],

#     # Color properties
#     "color": ["white", "black", "red", "green", "blue", "yellow", "orange", "purple", "pink", "gray", "brown", "transparent", 
#               "rgb(0, 0, 0)", "rgb(87, 87, 87)", "rgb(114, 114, 114)", "rgb(77, 172, 79)"],
#     "background-color": ["white", "black", "red", "green", "blue", "yellow", "orange", "purple", "pink", "gray", "brown", "transparent",
#                         "rgb(255, 255, 255)", "#fafafa"],

#     # Other properties
#     "object-fit": ["cover", "contain", "fill", "none", "scale-down"],
#     "aspect-ratio": ["3/4", "1/1", "16/9"]
# }




# tailwind_scale = [
#   "0px",
#   "1px",
#   "2px",
#   "4px",
#   "6px",
#   "8px",
#   "10px",
#   "12px",
#   "14px",
#   "16px",
#   "20px",
#   "24px",
#   "28px",
#   "32px",
#   "36px",
#   "40px",
#   "44px",
#   "48px",
#   "56px",
#   "64px",
#   "80px",
#   "96px",
#   "112px",
#   "128px",
#   "144px",
#   "160px",
# #   "176px",
# #   "192px",
# #   "208px",
# #   "224px",
# #   "240px",
# #   "256px",
# #   "288px",
# #   "320px",
# #   "384px"
# ]




