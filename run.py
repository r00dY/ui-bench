from dotenv import load_dotenv
load_dotenv()

import base64
import os
from openai import OpenAI

client = OpenAI()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--window-size=1536,1000")  # Set window size
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize driver
driver = webdriver.Chrome(options=chrome_options)



# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def run():

    design_system_preview_path = "data/pangaia/section1/design_system_preview.png"
    preview_path = "data/pangaia/section1/preview.png"

    design_system_preview_base64 = encode_image(design_system_preview_path)
    preview_base64 = encode_image(preview_path)

    # Load design system HTML
    with open("data/pangaia/section1/design_system.html", "r") as f:
        design_system_code = f.read()






    response = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You're a designer that knows how to code.

<objective>
You'll be given an image of a section of a website (rendered at 1536px wide screen size). Your job is to write the HTML and CSS for the section so that, when rendered, it looks exactly like the image.
- Return JUST HTML with inline CSS. I want to copy the response, paste into file.html and be able to preview. Do not add any extra markdown formatting. Just paste raw HTML/CSS. 
- For images, fonts, colors and icons, follow the instructions from <design_system_instructions>.
</objective>

<design_system_instructions>
All the images, fonts, colors and icons that you need are in an attached design system page. We give HTML of the design system page in <design_system_page>. Also, we're adding an image of the design system page so that you can see how things look (rendered at 1536px wide screen size, exactly the same as the section preview image).
</design_system_instructions>

<design_system_page>
{design_system_code}
</design_system_page>

Design system page preview image:
""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{design_system_preview_base64}",
                            "detail": "high"
                        },
                    },
                    {
                        "type": "text",
                        "text": """Section preview (the one you're supposed to write the HTML and CSS for):""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{preview_base64}", 
                            "detail": "high"
                        },
                    }
                ],
            }
        ],
    )

    # Extract just the HTML content
    content = response.choices[0].message.content
    
    # Find start and end of HTML
    start = content.find("<html")
    end = content.find("</html>") + 7
    
    if start >= 0 and end >= 0:
        content = content[start:end]


    # Find next available iteration number
    section_dir = "data/pangaia/section1"
    iteration = 1
    while os.path.exists(os.path.join(section_dir, f"iteration{iteration}_output1.html")):
        iteration += 1

    filename = f"iteration{iteration}_output1.html"

    # Save response to iterationX_output1.html
    output_path = os.path.join(section_dir, filename)
    with open(output_path, "w") as f:
        f.write(content)

    # Take screenshot of the generated HTML
    render_html_file(os.path.join(section_dir, filename))

    

def render_html_file(html_file_path):
    # Get just the filename for the URL
    base_filename = os.path.basename(html_file_path)
    
    # Set window size to 1536px width
    driver.set_window_size(1536, 1000)
    
    # Load the page
    url = f"http://localhost:8000/{base_filename}"
    driver.get(url)
    
    # Wait for page to load
    time.sleep(2)
    
    # Take screenshot with same path but .png extension
    screenshot_path = html_file_path.replace('.html', '.png')
    driver.save_screenshot(screenshot_path)
    
    # Cleanup
    driver.quit()


if __name__ == "__main__":
    # run()
    render_html_file("data/pangaia/section1/iteration1_output1.html")