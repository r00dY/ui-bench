from dotenv import load_dotenv
load_dotenv()

import base64
import json
import os
from bs4 import BeautifulSoup
from my_types import Config, StyleSheet
from copy import deepcopy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import html
from langfuse.openai import openai    
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import time


# Function to encode the image
def read_and_encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_json_from_response(response_text):
    # Try to find JSON block between code fence markers first
    if "```json" in response_text:
        # Extract content between ```json and ```
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        json_str = response_text[start:end].strip()
    elif "```" in response_text:
        # Extract content between ``` and ```
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        json_str = response_text[start:end].strip()
    else:
        # Try to find JSON object directly
        start = response_text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in response")
        # Find matching closing brace
        count = 1
        end = start + 1
        while count > 0 and end < len(response_text):
            if response_text[end] == "{":
                count += 1
            elif response_text[end] == "}":
                count -= 1
            end += 1
        json_str = response_text[start:end].strip()

    # Parse the extracted JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")


def generate_css_string(styles):
    css = []
    for selector, properties in styles.items():
        css.append(f"{selector} {{")
        for prop, value in properties.items():
            css.append(f"    {prop}: {value};")
        css.append("}")
        css.append("")
    return "\n" + "\n".join(css) + "\n"


def generate_html(project_id: str, page_id: str, styles: StyleSheet):
    # Read page.html
    page_path = os.path.join("data", project_id, "pages", page_id, "page.html")
    with open(page_path) as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # Find style tag and insert CSS
    style_tag = soup.find('style', id='page-styles')
    style_tag.string = generate_css_string(styles)

    # Add global CSS styles
    global_css_path = os.path.join("data", project_id, "global.css")
    if os.path.exists(global_css_path):
        with open(global_css_path) as f:
            global_css = f.read()
        
        # Find the link tag that references global.css
        global_link = soup.find('link', href=lambda href: href and "global.css" in href)
        if global_link:
            # Create a new style tag with global CSS content
            global_style = soup.new_tag('style', id="global-styles")
            global_style.string = global_css
            
            # Replace the link tag with the style tag
            global_link.replace_with(global_style)

    return soup.prettify()


def apply_css_changes(reference_css: StyleSheet, *changes: StyleSheet) -> StyleSheet:
    # Create deep copy of reference to avoid modifying original
    result = deepcopy(reference_css)
    
    # Apply each set of changes in order
    for change_set in changes:
        for selector, css_props in change_set.items():
            if selector in result:
                result[selector].update(css_props)
            else:
                # If selector doesn't exist, add it
                result[selector] = css_props
                
    return result


class BrowserManager:
    def __init__(self, max_concurrent_pages=10):
        self.playwright = None
        self.browser = None
        self.max_concurrent_pages = max_concurrent_pages
        self.active_pages = 0
        self._initialized = False
    
    async def initialize(self):
        if not self._initialized:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self._initialized = True
    
    async def close(self):
        if self._initialized:
            await self.browser.close()
            await self.playwright.stop()
            self._initialized = False
            self.active_pages = 0
    
    async def get_page(self, path):
        await self.initialize()
        
        # Wait for a page slot to become available
        while self.active_pages >= self.max_concurrent_pages:
            await asyncio.sleep(1)  # Simple sleep instead of semaphore
        
        self.active_pages += 1
        
        # Create context with viewport size
        context = await self.browser.new_context(viewport={"width": 1536, "height": 100})
        
        # Create page and set up console error logging
        page = await context.new_page()
        
        # Log console errors
        page.on("console", lambda msg: print(f"Browser console {msg.type}: {msg.text}") if msg.type == "error" else None)
        
        # Log page errors
        page.on("pageerror", lambda err: print(f"Page error: {err}"))
        
        # Log request failures
        page.on("requestfailed", lambda request: print(f"Request failed: {request.url} - {request.failure}"))
        
        # Navigate to the page
        url = f"http://localhost:8000/{path}"
        try:
            await page.goto(url, wait_until="networkidle")
        except Exception as e:
            print(f"Navigation error for {url}: {str(e)}")

        # Return page along with a release function
        async def release_page():
            await page.close()
            await context.close()
            self.active_pages -= 1
        
        return page, release_page

# Create a singleton instance
browser_manager = BrowserManager()

async def render_html(path):
    """Render HTML file and save screenshot with same basename"""
    
    # Get page and release function
    page, release_page = await browser_manager.get_page(path)
    
    try:
        # Get total height of page by getting scrollHeight of document element
        total_height = await page.evaluate("document.documentElement.scrollHeight")

        print(f"Total height: {total_height}")
        
        # Set viewport height to match content height
        await page.set_viewport_size({"width": 1536, "height": total_height})
        
        # Save screenshot with same basename but .png extension
        base_filename = os.path.splitext(path)[0]
        screenshot_path = os.path.join("data", f"{base_filename}.png")
        
        await page.screenshot(path=screenshot_path, full_page=True, scale="device")
    finally:
        # Always release the page when done
        await release_page()

        
async def get_computed_css(path):
    # Get page and release function
    page, release_page = await browser_manager.get_page(path)
    
    try:
        # Get the HTML content
        html_content = await page.content()
        
        # Use read_page_styles to extract selectors and properties
        stylesheet = read_page_styles(html_content)
        
        computed_values = {}
        
        for selector, properties in stylesheet.items():
            # Check if elements exist for this selector
            elements = await page.query_selector_all(selector)
            
            if not elements or len(elements) == 0:
                continue
                
            # Get first matching element's computed style
            computed_style = await page.evaluate("""
                (arg) => {
                    const [element, properties] = arg;
                    let computedStyle = window.getComputedStyle(element);
                    let values = {};
                    
                    properties.forEach((prop) => {
                        values[prop] = computedStyle.getPropertyValue(prop);
                    });
                    
                    return values;
                }
            """, [elements[0], list(properties.keys())])
            
            computed_values[selector] = computed_style
            
        return computed_values
    finally:
        # Always release the page when done
        await release_page()




def read_page_styles(html_content) -> StyleSheet:

    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the page-styles stylesheet
    page_styles = soup.select_one('#page-styles')
    if not page_styles:
        return {}  # Return empty stylesheet if not found
    
    # Extract CSS rules
    css_text = page_styles.string
    
    # Remove comments
    css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    
    stylesheet: StyleSheet = {}
    # Find all CSS rule blocks
    pattern = r'([^\{\}]+)\s*\{([^\{\}]*)\}'
    matches = re.findall(pattern, css_text)
    
    for selector, properties_text in matches:
        selector = selector.strip()
        
        # Skip if selector is empty
        if not selector:
            continue
        
        # Parse properties
        properties = {}
        for prop in properties_text.split(';'):
            prop = prop.strip()
            if not prop:
                continue
            
            try:
                key, value = prop.split(':', 1)
                properties[key.strip()] = value.strip()
            except ValueError:
                # Skip malformed properties
                continue
        
        stylesheet[selector] = properties
    
    return stylesheet


def load_config(project_id: str, page_id: str) -> Config:
    """
    Load and validate configuration for a specific project and page.
    
    Args:
        project_id (str): The ID of the project
        page_id (str): The ID of the page
    
    Returns:
        Config: Validated configuration object
    """
    # Construct paths
    html_path = os.path.join('data', project_id, 'pages', page_id, 'page.html')
    config_path = os.path.join('data', project_id, 'pages', page_id, 'config.json')
    
    # Read HTML file
    with open(html_path, 'r') as f:
        html_content = f.read()
    
    # Extract page styles
    stylesheet = read_page_styles(html_content)
    
    # Read config file
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Add correct CSS to config data
    config_data['correct_css'] = stylesheet
    
    # Validate and return config
    return Config.model_validate(config_data)

def prompt_content_to_html(content):
    prompt_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        img {{ max-width: 100%; }}
        .message {{ margin: 20px 0; padding: 20px; border: 1px solid #ccc; }}
    </style>
</head>
<body>"""

    for item in content:
        if item["type"] == "text":
            prompt_html += f"""
<div class="message">
    <pre>{html.escape(item["text"])}</pre>
</div>"""
        elif item["type"] == "image_url":
            prompt_html += f"""
<div class="message">
    <img src="{item["image_url"]["url"]}" />
</div>"""

    prompt_html += """
</body>
</html>"""

    return prompt_html



async def call_openrouter_with_retry(messages, model, response_format, max_retries=5, timeout=10, name=None):
    try:
        client = openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            max_retries=max_retries, 
            timeout=timeout
        )

        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            name=name
        )

        content = completion.choices[0].message.content

        try:
            response_object = response_format.model_validate(extract_json_from_response(content))
        except Exception as e:
            return {"error": "json_format_error", "message": str(e)}

        return { "content": response_object }

    except Exception as e:
        return {"error": "api_error", "message": str(e)}

