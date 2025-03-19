import sys          
import os
import json
from pathlib import Path


def generate_css(fonts, dir_path):
    css_content = []
    for font in fonts:
        if 'urls' not in font or not font['urls']:
            continue
            
        font_family = font.get('font-family', '')
        if not font_family:
            continue
            
        font_url = font['urls'][0]  # Use the original external URL
        # Add protocol if missing
        if font_url.startswith('//'):
            font_url = 'https:' + font_url
            
        font_weight = font.get('font-weight', 'normal')
        font_style = font.get('font-style', 'normal')
        
        css_content.append(f"""@font-face {{
    font-family: '{font_family}';
    src: url('{font_url}') format('woff2');
    font-weight: {font_weight};
    font-style: {font_style};
}}""")
    
    # Write the CSS file
    css_path = os.path.join(dir_path, 'fonts.css')
    try:
        with open(css_path, 'w') as f:
            f.write('\n\n'.join(css_content))
    except Exception as e:
        print(f"Failed to write fonts.css: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python get_fonts.py <directory_path>")
        sys.exit(1)
        
    dir_path = sys.argv[1]
    
    # Read fonts_source.json
    try:
        with open(os.path.join(dir_path, 'fonts_source.json')) as f:
            fonts = json.load(f)
    except Exception as e:
        print(f"Failed to read fonts_source.json: {str(e)}")
        sys.exit(1)

    # Generate CSS file with external URLs
    try:
        generate_css(fonts, dir_path)
    except Exception as e:
        print(f"Failed to generate fonts.css: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
