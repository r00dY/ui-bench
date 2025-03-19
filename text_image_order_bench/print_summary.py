import os
import json
from pathlib import Path
from typing import Dict, List
from text_image_order_bench.shared import ROOT_DIR


def calculate_success_percentage(results: List[Dict]) -> float:
    """Calculate the percentage of successful results."""
    if not results:
        return 0.0
    
    correct_count = sum(1 for item in results if item.get("result", {}).get("model_correct", False))
    return (correct_count / len(results)) * 100

def print_model_results() -> None:
    """Print success percentage for each model."""
    results_dir = os.path.join(ROOT_DIR, "results")
    
    print("\nText-Image Order Benchmark Results")
    print("==================================")
    print(f"{'Model ID':<45} | {'Success %':<10}")
    print(f"{'-' * 45} | {'-' * 10}")
    
    # Get all model directories
    model_dirs = [d for d in Path(results_dir).iterdir() if d.is_dir()]
    
    # Collect results for all models
    model_results = []
    
    for model_dir in model_dirs:
        model_id = model_dir.name.replace('_', '/')
        results_file = model_dir / "results.json"
        
        if not results_file.exists():
            model_results.append((model_id, "No results file", None))
            continue
        
        try:
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            success_percentage = calculate_success_percentage(results)
            model_results.append((model_id, success_percentage, None))
            
        except Exception as e:
            model_results.append((model_id, f"Error: {str(e)}", None))
    
    # Sort by success percentage (highest first)
    # Items with errors or no results will be at the end
    sorted_results = sorted(
        model_results, 
        key=lambda x: float('-inf') if isinstance(x[1], str) else x[1],
        reverse=True
    )
    
    # Print sorted results
    for model_id, result, _ in sorted_results:
        if isinstance(result, str):
            print(f"{model_id:<45} | {result}")
        else:
            print(f"{model_id:<45} | {result:.2f}%")

if __name__ == "__main__":
    print_model_results()
