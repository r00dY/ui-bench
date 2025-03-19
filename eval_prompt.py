def eval_prompt(errors_count, incorrect_html, incorrect_image, correct_image):
    return [
        {
            "type": "text",
            "text": f"""You are a design expert. I will show you:
1. A webpage's HTML code with its current screenshot - this represents an INCORRECT design with styling errors. This page is called "incorrect.html".
2. A "correct design" screenshot showing how the webpage SHOULD look. The correct page is called "correct.html".

Your task is to identify what CSS values need to be modified to match the correct design. Number of values to be fixed is: {errors_count}.

Important notes:
- The webpage contains a single section for simplicity 
- The HTML has two style sections: #global-styles and #page-styles
- All styling errors are ONLY in the #page-styles section
- The HTML uses simple markup with descriptive class names
- The styling errors were made ONLY by changing existing CSS property values
- DO NOT add or remove any CSS properties - only modify existing values
- Number of CSS values to be fixed is: {errors_count}
- The #global-styles section should not be modified, it's 100% correct

Please analyze the differences and provide your response in EXACTLY this JSON format with no additional text or explanation:
""" + """
{
    "reasoning": "Explain the visual differences and what needs to be fixed",
    "css_changes": {
        ".example-class": {
            "property-name": "value",
            "another-property": "value2"
        },
        ".another-class": {
            "some-property": "value"
        }
    }
}

Any other format will not be processed correctly. Your response must be valid JSON that matches this exact structure.

Here is the incorrect page HTML code (incorrect.html):

""" + " " + incorrect_html
        },
        {
            "type": "text",
            "text": "The screenshot of incorrect page design (incorrect.html) that needs to be fixed:"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": incorrect_image
            }
        },
        {
            "type": "text",
            "text": "The correct page design (a screenshot of correct.html):"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": correct_image
            }
        }
    ]