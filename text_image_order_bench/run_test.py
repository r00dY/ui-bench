from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import asyncio
import aiohttp
import time
from utils import extract_json_from_response
from text_image_order_bench.shared import ANIMALS_DICT

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RATE_LIMIT_DELAY = 10  # seconds to wait when rate limited

def create_message_content(test_items):
    """Create a message content with interleaved text and images."""
    content = [
        {
            "type": "text",
            "text": "Look at these animals and tell me if the labels match the images correctly. "
                    "Respond ONLY with a valid JSON object in this exact format: "
                    "{\"all_labels_correct\": true} if all labels are correct, or "
                    "{\"all_labels_correct\": false} if any labels are incorrect. "
                    "Do not include any additional text, explanation, or markdown formatting."
        }
    ]
    
    for item in test_items:
        # Add the displayed label
        content.append({
            "type": "text",
            "text": f"{ANIMALS_DICT[item["label"]].label}:"
        })
        
        # Add the image using the animal's encoded image URL
        content.append({
            "type": "image_url",
            "image_url": {
                "url": ANIMALS_DICT[item["image"]].image_url
            }
        })
    
    return content





async def call_model_with_retry(content, model, max_retries=5):
    """Call the model with retry logic for rate limiting."""
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": content
            }
        ]
    }
    
    retries = 0
    while retries <= max_retries:
        try:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response_data = await response.json()

                    # Check if there's an error in the response
                    if "error" in response_data:
                        error_code = response_data["error"].get("code")
                        error_message = response_data["error"].get("message", "Unknown API error")
                        
                        # Handle rate limiting
                        if error_code == 429:
                            retries += 1
                            if retries <= max_retries:
                                print(f"Rate limited for model {model}. Retrying in {RATE_LIMIT_DELAY}s... (Attempt {retries}/{max_retries})")
                                await asyncio.sleep(RATE_LIMIT_DELAY)
                                continue
                            else:
                                return {"error": "rate_limit", "message": error_message}
                        else:
                            return {"error": "api_error", "message": error_message}
                    
                    return {"success": True, "content": response_data["choices"][0]["message"]["content"]}
        except Exception as e:
            retries += 1
            if retries <= max_retries:
                print(f"Error during API call for model {model}: {e}. Retrying in {RATE_LIMIT_DELAY}s... (Attempt {retries}/{max_retries})")
                await asyncio.sleep(RATE_LIMIT_DELAY)
            else:
                return {"error": "max_retries_exceeded", "message": str(e)}
    
    return {"error": "max_retries_exceeded", "message": "Maximum retries exceeded"}

async def process_model_response(model_response_data, reference_correct: bool):
    """Process the model response and handle potential errors."""
    if "error" in model_response_data:
        return {
            "success": False,
            "error_type": model_response_data["error"],
            "error_message": model_response_data["message"],
            "model_correct": False
        }
    
    try:
        # Extract and validate JSON response
        model_response_text = model_response_data["content"]
        model_response = extract_json_from_response(model_response_text)
        
        # Validate that model_response has the expected structure
        if "all_labels_correct" not in model_response:
            return {
                "success": False,
                "error_type": "format_error",
                "error_message": f"Response missing 'all_labels_correct' key: {model_response}",
                "model_correct": False
            }
            
        if not isinstance(model_response["all_labels_correct"], bool):
            return {
                "success": False,
                "error_type": "format_error",
                "error_message": f"'all_labels_correct' is not a boolean value: {model_response['all_labels_correct']}",
                "model_correct": False
            }
        
        return {
            "success": True,
            "model_response": model_response,
            "model_correct": model_response["all_labels_correct"] == reference_correct
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": "processing_error",
            "error_message": str(e),
            "model_correct": False
        }

async def run_test_for_model(test_case, model):
    """Run a single test case for a specific model."""
    # Create the message content
    content = create_message_content(test_case["items"])
    
    # Call the model with retry logic
    model_response_data = await call_model_with_retry(content, model)
    
    # Process the response
    result = await process_model_response(model_response_data, test_case["correct"])
    
    output = {
        **test_case,
        "result": result
    }

    id = test_case["id"]

    # Log the result
    if result["success"]:
        print(f"Test {id} - Model correct?: {result['model_correct']}")
    else:
        print(f"Test {id} - Error: {result['error_type']} - {result['error_message']}")
    
    return output

async def run_tests(model_id):
    """Run all tests for the specified model."""
    
    # Load test cases from JSON file
    print("Loading test cases...")
    test_cases_path = os.path.join(ROOT_DIR, "test_cases.json")
    with open(test_cases_path, "r") as f:
        test_cases = json.load(f)
    print(f"Loaded {len(test_cases)} test cases successfully.")
    
    # Run all test cases for the specified model
    print(f"Running {len(test_cases)} test cases for model {model_id}...")
    tasks = []
    for test_case in test_cases:
        task = run_test_for_model(test_case,  model_id)
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(ROOT_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Create model-specific directory
    model_dir = os.path.join(results_dir, model_id.replace('/', '_'))
    os.makedirs(model_dir, exist_ok=True)
    
    # Save results to file
    results_file = os.path.join(model_dir, "results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=4)
    
    # Generate summary
    correct_count = sum(1 for r in results if r.get("result", {}).get("model_correct", False))
    success_count = sum(1 for r in results if r.get("result", {}).get("success", False))
    
    summary = "\n===== TEST RESULTS SUMMARY =====\n"
    summary += f"\nModel: {model_id}\n"
    summary += f"  Total tests: {len(results)}\n"
    summary += f"  Successful tests: {success_count} ({success_count / len(results):.2%})\n"
    summary += f"  Correct tests: {correct_count} ({correct_count / len(results):.2%})\n"
    summary += f"\nResults saved to results/{model_id.replace('/', '_')}/results.json"
    
    # Print summary
    print(summary)

    # Save summary to text file
    summary_file = os.path.join(model_dir, "summary.txt")
    with open(summary_file, "w") as f:
        f.write(summary)
    
    print(f"Summary saved to results/{model_id.replace('/', '_')}/summary.txt")
    
    return results

def keep_program_running():
    """Keep the program running after tests are completed."""
    print("\nTests completed. Program will remain running until manually stopped.")
    print("Press Ctrl+C to exit.")
    try:
        # Keep the program running until manually interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_test.py <model_id>")
        sys.exit(1)
    
    model_id = sys.argv[1]
    
    # Add a command-line flag to keep the program running after tests
    keep_running = False
    if len(sys.argv) > 2 and sys.argv[2] == "--keep-running":
        keep_running = true
    
    results = asyncio.run(run_tests(model_id))
    
    if keep_running:
        keep_program_running()
    else:
        print("\nAll tests completed. Program will now exit.")
        # Program naturally exits here
