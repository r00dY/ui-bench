import json
import os
from my_types import Config
from utils import generate_html, apply_css_changes, read_page_styles, load_config

def run_html(project_id, page_id, variant_id):
    page_dir = f"data/{project_id}/pages/{page_id}"

    # Read and parse styles.json into Config object
    config = load_config(project_id, page_id)
        
    # Create generated directory if it doesn't exist
    generated_dir = os.path.join(page_dir, "generated")
    os.makedirs(generated_dir, exist_ok=True)

    if variant_id == "reference":
        # Generate reference HTML
        reference_html = generate_html(project_id, page_id, config.correct_css)
        
        # Save as reference.html
        output_path = os.path.join(generated_dir, "reference.html") 
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(reference_html)
    else:
        variant = config.get_variant(variant_id)
        
        # Generate variant HTML
        variant_css = apply_css_changes(config.correct_css, variant.css_changes)
        variant_html = generate_html(project_id, page_id, variant_css)

        # Save variant file
        
        # Create variant directory if it doesn't exist
        variant_dir = os.path.join(generated_dir, variant.id)
        os.makedirs(variant_dir, exist_ok=True)
        
        # Save result in index.html in the variant directory
        variant_path = os.path.join(variant_dir, "page.html")
        with open(variant_path, "w", encoding='utf-8') as f:
            f.write(variant_html)
