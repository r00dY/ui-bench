import json
import random
import os
from itertools import permutations
from text_image_order_bench.shared import ANIMALS

def generate_test_cases(num_cases):
    """
    Generate test cases with random animals and shuffled labels.
    
    Args:
        num_cases: Number of test cases to generate
    
    Returns:
        List of test case dictionaries
    """
    test_cases = []

    for i in range(num_cases):
        # Randomly select 2-4 animals
        num_animals = random.randint(2, 4)
        selected_animals = random.sample(ANIMALS, num_animals)
        
        # Get the animal IDs
        animal_ids = [animal.id for animal in selected_animals]
        
        # Create a shuffled version of the IDs for labels
        shuffled_ids = animal_ids.copy()
        random.shuffle(shuffled_ids)
        
        # Check if the shuffling created a correct or incorrect case
        is_correct = (animal_ids == shuffled_ids)
        
        # Create the items list
        items = [{"label": label, "image": image} 
                for label, image in zip(shuffled_ids, animal_ids)]
        
        test_cases.append({
            "correct": is_correct,
            "items": items
        })
    
    # Shuffle the test cases
    random.shuffle(test_cases)
    
    # Add ID for each test case from 1
    for i, test_case in enumerate(test_cases, 1):
        # Create a new dict with id first, then copy all other items
        new_test_case = {"id": i}
        new_test_case.update(test_case)
        test_cases[i-1] = new_test_case
    return test_cases

def save_test_cases(test_cases, filename="test_cases.json"):
    """Save test cases to a JSON file"""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath, 'w') as f:
        json.dump(test_cases, f, indent=4)
    print(f"Saved {len(test_cases)} test cases to {filepath}")
    
    # Print distribution of true/false test cases
    true_count = sum(1 for case in test_cases if case["correct"] is True)
    false_count = sum(1 for case in test_cases if case["correct"] is False)
    print(f"Distribution of test cases:")
    print(f"  - Correct (True): {true_count} ({true_count/len(test_cases)*100:.1f}%)")
    print(f"  - Incorrect (False): {false_count} ({false_count/len(test_cases)*100:.1f}%)")
    
    # Calculate and print distribution of error percentages by animal count
    error_stats = {}
    for case in test_cases:
        if not case["correct"]:
            # Count total items and mismatched items
            items = case["items"]
            total_items = len(items)
            mismatched = sum(1 for item in items if item["label"] != item["image"])
            error_rate = mismatched / total_items * 100
            
            # Create keys for grouping by animal count and error percentage
            animal_count_key = f"{total_items} animals"
            error_rate_key = f"{error_rate:.0f}%"
            
            # Initialize nested dictionary if needed
            if animal_count_key not in error_stats:
                error_stats[animal_count_key] = {}
            
            if error_rate_key not in error_stats[animal_count_key]:
                error_stats[animal_count_key][error_rate_key] = 0
            
            error_stats[animal_count_key][error_rate_key] += 1
    
    print(f"Detailed distribution of errors in incorrect test cases:")
    for animal_count in sorted(error_stats.keys(), key=lambda x: int(x.split()[0])):
        animal_count_total = sum(error_stats[animal_count].values())
        print(f"  {animal_count} ({animal_count_total} cases):")
        
        for error_rate, count in sorted(error_stats[animal_count].items(), key=lambda x: float(x[0][:-1])):
            percentage = count / animal_count_total * 100
            print(f"    - {error_rate} errors: {count} cases ({percentage:.1f}% of {animal_count} cases)")

if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(253)
    
    # Generate test cases
    test_cases = generate_test_cases(num_cases=100)
    
    # Save test cases to file
    save_test_cases(test_cases)
