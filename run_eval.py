from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel
load_dotenv()

import os
import sys
import json
from my_types import Config, StyleSheet
from langfuse.openai import OpenAI
from utils import apply_css_changes, generate_html, get_computed_css, load_config, read_and_encode_image, render_html, prompt_content_to_html, call_openrouter_with_retry
from css_properties import css_properties
from eval_prompt import eval_prompt

RATE_LIMIT_DELAY = 10

class Response(BaseModel):
    reasoning: str
    css_changes: StyleSheet

async def run_eval(project_id, page_id, variant_id, model, test=False):
    page_dir = f"data/{project_id}/pages/{page_id}"

    config = load_config(project_id, page_id)

    # Process model name for filename compatibility
    # Replace slash characters with underscores to make it safe for filenames
    model_id = model.replace("/", "_")

    # Validate variant exists
    variant = config.get_variant(variant_id)

    if not variant:
        print(f"Variant {variant_id} not found in config.json")
        sys.exit(1)

    # Load variant and reference files
    variant_html_path = os.path.join(page_dir, "generated", variant.id, f"page.html")
    variant_png_path = os.path.join(page_dir, "generated", variant.id, f"page.png") 
    reference_png_path = os.path.join(page_dir, "generated", "reference.png")
    eval_result_path = os.path.join(page_dir, "generated", variant.id, model_id, f"result.json")

    # Create directory for model results if it doesn't exist
    model_result_dir = os.path.dirname(eval_result_path)
    if not os.path.exists(model_result_dir):
        os.makedirs(model_result_dir)


    if os.path.exists(eval_result_path) and not test:
        try:
            with open(eval_result_path, 'r') as f:
                result_data = json.load(f)
                
            # Only skip if there's no API error
            if not (result_data.get("error_code") == "api_error"):
                print(f"[eval] {project_id}.{page_id}.{variant.id} - Evaluation result already exists. Skipping...")
                return
            # If there was an API error, we'll continue with the evaluation
        except json.JSONDecodeError:
            # If the file exists but isn't valid JSON, continue with evaluation
            pass

    # Load HTML content
    with open(variant_html_path, "r") as f:
        variant_html = f.read()

    # Encode images
    variant_png_base64 = read_and_encode_image(variant_png_path)
    reference_png_base64 = read_and_encode_image(reference_png_path)

#     design_system_prompt = """
# You must only use CSS values from predefined lists for each property type:

# For spacing properties (margin, padding, gap, top/left/bottom/right, width, height):
# Use values from the space scale: 0px, 1px, 2px, 4px, 6px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px, 128px, 160px

# For `width` and `height` you can also use `auto` or `%` values. 

# For font sizes:
# 10px, 12px, 14px, 16px, 20px, 24px, 28px, 32px

# For colors following values are allowed:
# - `white`, `black`, `red`, `green`, `blue`, `yellow`, `orange`, `purple`, `pink`, `gray`, `brown`, `transparent`

# `display`: `flex`, `grid`, `absolute`, `relative`, `block`, `inline-block`, `inline`, `none`

# `position`: `static`, `relative`, `absolute`, `fixed`, `sticky`

# `flex-direction`: `row`, `row-reverse`, `column`, `column-reverse`

# `justify-content`: `flex-start`, `flex-end`, `center`, `space-between`, `space-around`, `space-evenly`

# `align-items`: `flex-start`, `flex-end`, `center`, `baseline`, `stretch`



# For other properties:
# Only use values that appear in the original correct CSS


# """

    errors_count = len(variant.css_changes.keys())

    prompt = eval_prompt(
        errors_count=errors_count, 
        incorrect_html=variant_html, 
        incorrect_image=f"data:image/png;base64,{variant_png_base64}",
        correct_image=f"data:image/png;base64,{reference_png_base64}"
    )

    # Save prompt HTML
    prompt_html = prompt_content_to_html(prompt)
    prompt_output_path = os.path.join(page_dir, "generated", variant_id, f"prompt.html")
    with open(prompt_output_path, "w") as f:
        f.write(prompt_html)


    def save_eval_result(error_code, error_details=None):
        eval_result = {
            "passed": error_code is None
        }

        if error_code:
            eval_result["error_code"] = error_code

        if error_details:
            eval_result["error_details"] = error_details

        # Save evaluation result
        with open(eval_result_path, "w", encoding='utf-8') as f:
            json.dump(eval_result, f, indent=2)

        print(f"[eval] {project_id}.{page_id}.{variant.id} - finished, correct: {error_code is None}, error: {error_code} ({error_details})")

    
    # Call OpenAI API
    if not test:
        response_full = await call_openrouter_with_retry(
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            model=model, 
            response_format=Response,
            name=f"{project_id}.{page_id}.{variant_id}.{model_id}"
        )

        if "error" in response_full:
            save_eval_result(response_full["error"], response_full["message"])
            return

        response = response_full["content"]

    else:
        if not config.test__corrected_css:
            raise ValueError(f"Variant {variant_id} does not have a test corrected CSS, so can't run test mode.")
        
        # Extract only the properties that were changed in variant.css_changes
        test__corrected_css : StyleSheet = {}
        for selector, properties in variant.css_changes.items():
            if selector in config.test__corrected_css:
                test__corrected_css[selector] = {}
                for prop_name in properties.keys():
                    if prop_name in config.test__corrected_css[selector]:
                        test__corrected_css[selector][prop_name] = config.test__corrected_css[selector][prop_name]

        response = Response(reasoning="I'm a sneaky test set destined to succeeed", css_changes=test__corrected_css)

    
    # Save response JSON
    json_output_path = os.path.join(page_dir, "generated", variant_id, model_id, "response.json")
    with open(json_output_path, "w") as f:
        json.dump(response.model_dump(), f, indent=4)

    try:
        config.verify_css_changes(response.css_changes)
    except ValueError as e:
        save_eval_result("invalid_css_changes", str(e))
        return

    # Evaluate the response (result is 0-1 basically)
    corrected_page_css = apply_css_changes(config.correct_css, variant.css_changes, response.css_changes)
    corrected_page_html = generate_html(project_id, page_id, corrected_page_css)

    # Save LLM generated HTML
    corrected_page_output_path = os.path.join(page_dir, "generated", variant_id, model_id, "page.html")
    with open(corrected_page_output_path, "w", encoding='utf-8') as f:
        f.write(corrected_page_html)

    print(f"[eval] {project_id}.{page_id}.{variant_id} - Generating pages")

    await render_html(f"{project_id}/pages/{page_id}/generated/{variant_id}/{model_id}/page.html")

    # Get computed values for reference and corrected pages
    reference_computed = await get_computed_css(f"{project_id}/pages/{page_id}/generated/reference.html")
    corrected_computed = await get_computed_css(f"{project_id}/pages/{page_id}/generated/{variant_id}/{model_id}/page.html")

    # # Save reference computed values
    # reference_computed_path = os.path.join(page_dir, "generated", "reference.computed_values.json")
    # with open(reference_computed_path, "w", encoding='utf-8') as f:
    #     json.dump(reference_computed, f, indent=2)


    ### EVAL STEP 1. Check if model identified the correct CSS properties to fix

    # Check if model identified the correct CSS properties to fix
    error_code = None
    error_details = None
    
    # Convert variant changes to set of tuples for comparison
    variant_changes_set = {
        (selector, prop_name)
        for selector, properties in variant.css_changes.items()
        for prop_name in properties.keys()
    }

    # Convert response changes to set of tuples for comparison
    response_changes_set = {
        (selector, prop_name)
        for selector, properties in response.css_changes.items() 
        for prop_name in properties.keys()
    }

    # Check if sets match exactly
    if variant_changes_set != response_changes_set:
        missing = variant_changes_set - response_changes_set
        extra = response_changes_set - variant_changes_set
        
        errors_arr = []
        if missing:
            missing_str = ", ".join([f"{s} -> {p}" for s,p in missing])
            errors_arr.append(f"missing: {missing_str}")
        if extra:
            extra_str = ", ".join([f"{s} -> {p}" for s,p in extra])
            errors_arr.append(f"unneccessary: {extra_str}")
            
        error_code = "wrong_css_properties"
        error_details = ", ".join(errors_arr)


    ### EVAL STEP 2. Check if model identified the correct CSS values to fix

    if error_code is None:
        
        # For each CSS change in the response, validate using property-specific evaluator
        for selector, properties in response.css_changes.items():
            for prop_name, new_value in properties.items():
                # Get evaluator function for this property
                evaluator = css_properties[prop_name]
                
                if evaluator is None:
                    error_code = "css_property_without_evaluator"
                    error_details = f"No evaluator defined for CSS property '{prop_name}'"
                    break
                
                # Get reference and corrected values to compare
                reference_value = reference_computed[selector][prop_name]
                corrected_value = corrected_computed[selector][prop_name]
                
                # Run the evaluator
                if not evaluator(reference_value, corrected_value):

                    error_code = "wrong_css_value"
                    error_details = f"Invalid value for {selector} -> {prop_name}:\n"
                    error_details += f"Expected (reference): {reference_value}\n"
                    error_details += f"Got (corrected): {corrected_value}"
                    break

    save_eval_result(error_code, error_details)
