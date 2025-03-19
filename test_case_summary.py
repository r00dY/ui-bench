import os
import json
from utils import load_config

def get_project_pages():
    """Get all project and page IDs from the data directory."""
    projects = {}
    
    # Walk through the data directory
    for project_id in os.listdir("data"):
        project_path = os.path.join("data", project_id)
        
        # Check if this is a directory and has a pages subdirectory
        pages_path = os.path.join(project_path, "pages")
        if os.path.isdir(project_path) and os.path.isdir(pages_path):
            projects[project_id] = []
            
            # Get all page IDs for this project
            for page_id in os.listdir(pages_path):
                page_path = os.path.join(pages_path, page_id)
                config_path = os.path.join(page_path, "config.json")
                
                # Check if this is a directory and has a config.json file
                if os.path.isdir(page_path) and os.path.exists(config_path):
                    projects[project_id].append(page_id)
    
    return projects

def count_variants(project_id, page_id):
    """Count variants for a specific project and page."""
    try:
        config = load_config(project_id, page_id)
        return len(config.variants) if hasattr(config, "variants") else 0
    except Exception as e:
        print(f"Error loading config for {project_id}/{page_id}: {e}")
        return 0

def main():
    projects = get_project_pages()
    total_variants = 0
    
    print("\n=== Test Case Summary ===\n")
    
    for project_id, page_ids in projects.items():
        print(f"Project: {project_id}")
        
        for page_id in page_ids:
            variant_count = count_variants(project_id, page_id)
            total_variants += variant_count
            print(f"  Page: {page_id} - {variant_count} variants")
        
        print()  # Empty line between projects
    
    print(f"Total number of variants across all projects: {total_variants}")

if __name__ == "__main__":
    main()
