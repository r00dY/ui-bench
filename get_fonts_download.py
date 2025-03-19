import sys
import os
import json
import requests
from urllib.parse import urlparse
from pathlib import Path

def download_font(url, save_path):
    try:
        # Add protocol if missing
        if url.startswith('//'):
            url = 'https:' + url
            
        response = requests.get(url)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {str(e)}")
        return False

def generate_css(fonts, dir_path):
    css_content = []
    for font in fonts:
        if 'urls' not in font or not font['urls']:
            continue
            
        font_family = font.get('font-family', '')
        if not font_family:
            continue
            
        font_url = font['urls'][0]  # We're using the first URL (local path)
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
    
    # Create fonts directory if it doesn't exist
    fonts_dir = os.path.join(dir_path, 'fonts')
    Path(fonts_dir).mkdir(parents=True, exist_ok=True)
    
    # Process each font
    for font in fonts:
        success = False
        
        for url in font['urls']:
            # Extract filename from URL
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = url.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
                
            save_path = os.path.join(fonts_dir, filename)
            
            if download_font(url, save_path):
                # Update URL to local path
                font['urls'] = [f'/fonts/{filename}']
                success = True
                break
                
        if not success:
            print(f"Failed to download font {font.get('font-family', 'Unknown')}")
    
    # Save updated fonts.json
    try:
        with open(os.path.join(dir_path, 'fonts.json'), 'w') as f:
            json.dump(fonts, f, indent=4)
            
        # Generate CSS file
        generate_css(fonts, dir_path)
    except Exception as e:
        print(f"Failed to write fonts.json: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
