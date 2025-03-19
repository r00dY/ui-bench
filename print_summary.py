import os
import json
from utils import load_config

def print_summary():
    # Define the models we want to track
    models = ["anthropic_claude-3.7-sonnet", "openai_chatgpt-4o-latest"]
    
    # Initialize results dictionary
    results = {model: {"passed": 0, "failed": 0, "total": 0} for model in models}
    
    # Walk through the data directory
    for project_id in os.listdir("data"):
        project_path = os.path.join("data", project_id)
        
        # Skip if not a directory
        if not os.path.isdir(project_path):
            continue
            
        pages_path = os.path.join(project_path, "pages")
        if not os.path.isdir(pages_path):
            continue
            
        # Iterate through sections
        for section_id in os.listdir(pages_path):
            section_path = os.path.join(pages_path, section_id)
            
            # Skip if not a directory
            if not os.path.isdir(section_path):
                continue
                
            # Load config for this section
            try:
                config = load_config(project_id, section_id)
                
                # Process each variant
                for variant in config.variants:
                    variant_id = variant.id
                    
                    # Check results for each model
                    for model in models:
                        result_path = os.path.join(section_path, "generated", variant_id, model, "result.json")
                        
                        # Skip if result file doesn't exist
                        if not os.path.exists(result_path):
                            continue
                            
                        # Read and process result
                        try:
                            with open(result_path, 'r') as f:
                                result_data = json.load(f)
                                
                            # Update statistics
                            results[model]["total"] += 1
                            if result_data.get("passed", False):
                                results[model]["passed"] += 1
                            else:
                                results[model]["failed"] += 1
                                
                        except Exception as e:
                            print(f"Error processing result for {project_id}.{section_id}.{variant_id}.{model}: {e}")
                
            except Exception as e:
                print(f"Error loading config for {project_id}.{section_id}: {e}")
    
    # Print summary
    print("\n===== EVALUATION SUMMARY =====")
    print(f"{'Model':<30} {'Passed':<10} {'Failed':<10} {'Total':<10} {'Pass Rate':<10}")
    print("-" * 70)
    
    for model, stats in results.items():
        pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"{model:<30} {stats['passed']:<10} {stats['failed']:<10} {stats['total']:<10} {pass_rate:.2f}%")

if __name__ == "__main__":
    print_summary()
