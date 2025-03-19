import json
import os
import argparse
from run_html import run_html
from run_screenshot import run_screenshot
from run_eval import run_eval
import asyncio
import sys

async def run():
    parser = argparse.ArgumentParser(description='Run evaluation')
    parser.add_argument('command', choices=['html', 'screenshot', 'eval'], help='Command to execute')
    parser.add_argument('testcase', help='Test case')
    parser.add_argument('--test', action='store_true', default=False, help='Run with test config data')
    parser.add_argument('--model', help='Model to use for evaluation (required for eval command)')

    args = parser.parse_args()

    if (args.command == "eval" and not args.model):
        print("Error: 'model' argument is required for 'eval' command")
        sys.exit(1)

    def parse_testcase(testcase: str) -> list[tuple[str, str, str]]:
        result = []
        for tc in testcase.split(','):
            parts = tc.strip().split('.')
            project = parts[0]
            
            if len(parts) == 1:
                pages_dir = os.path.join('data', project, 'pages')
                pages = [d for d in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, d))]
            else:
                pages = [parts[1]]
                
            for page in pages:
                config_path = os.path.join('data', project, 'pages', page, 'config.json')
                with open(config_path) as f:
                    config_dict = json.load(f)
                
                variants = [parts[2]] if len(parts) == 3 else [v['id'] for v in config_dict.get('variants', [])]
                
                # Add reference variant if using wildcard in html/screenshot commands
                if args.command in ["html", "screenshot"] and len(parts) < 3:
                    variants.append("reference")
                    
                result.extend((project, page, variant) for variant in variants)
        return result
    
    testcases = parse_testcase(args.testcase)
    
    if args.command in ["eval", "screenshot"]:
        # Run all tasks in parallel
        tasks = []
        for project_id, page_id, variant_id in testcases:
            print (f"[{args.command}] {project_id}.{page_id}.{variant_id} - started")
            if args.command == "eval":
                tasks.append(run_eval(project_id, page_id, variant_id, args.model, args.test))
            else:  # screenshot
                tasks.append(run_screenshot(project_id, page_id, variant_id))
        
        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks)
            
    else:
        # Run html tasks sequentially
        for project_id, page_id, variant_id in testcases:
            if args.command == "html":
                print ("[html] " + project_id + "." + page_id + "." + variant_id)
                run_html(project_id, page_id, variant_id)

if __name__ == "__main__":
    asyncio.run(run())