(function () {
    function listFontFaceRules() {
      // Gather all @font-face CSS rules from same-origin stylesheets
      const fontFaceRules = [];
      for (const sheet of document.styleSheets) {
        try {
          if (!sheet.cssRules) continue;
          for (const rule of sheet.cssRules) {
            if (rule.type === CSSRule.FONT_FACE_RULE) {
              fontFaceRules.push(rule);
            }
          }
        } catch (e) {
          console.warn("Could not access stylesheet", sheet.href, e);
        }
      }
  
      // Process and dedupe the rules
      const result = fontFaceRules.reduce((unique, rule) => {
        const fontFamily = rule.style.getPropertyValue("font-family").replace(/["']/g, "").trim();
        
        // Check if this font is used anywhere in the document
        const isUsed = Array.from(document.querySelectorAll('*')).some(element => {
          const computedStyle = window.getComputedStyle(element);
          return computedStyle.fontFamily.includes(fontFamily);
        });

        if (!isUsed) {
          return unique;
        }
        
        // Extract URLs from src property
        const src = rule.style.getPropertyValue("src");
        const urls = [];
        const urlRegex = /url\(["']?([^"')]+)["']?\)/g;
        let match;
        while ((match = urlRegex.exec(src)) !== null) {
          urls.push(match[1]);
        }
  
        // Check for duplicate font-family + font-style + font-weight combination
        const existing = unique.find(f => 
          f["font-family"] === fontFamily && 
          f["font-style"] === rule.style.getPropertyValue("font-style") &&
          f["font-weight"] === rule.style.getPropertyValue("font-weight")
        );
  
        if (!existing && urls.length > 0) {
          const properties = {
            "font-family": fontFamily,
            "urls": urls
          };

          // Only add properties that have values
          const styleProps = {
            "font-style": rule.style.getPropertyValue("font-style"),
            "font-weight": rule.style.getPropertyValue("font-weight"), 
            "font-stretch": rule.style.getPropertyValue("font-stretch"),
            // "font-display": rule.style.getPropertyValue("font-display"),
            "unicode-range": rule.style.getPropertyValue("unicode-range"),
            "font-feature-settings": rule.style.getPropertyValue("font-feature-settings")
          };

          for (const [key, value] of Object.entries(styleProps)) {
            if (value) {
              properties[key] = value;
            }
          }

          unique.push(properties);
        }
        return unique;
      }, []);
  
      return result;
    }
  
    // Example usage: log the data structure to the console
    const fontsData = listFontFaceRules();
    console.log(fontsData);
    
    // Create CSS @font-face rules from the fontsData array
    function createFontFaceCss(fontsData) {
      let css = '';
      
      fontsData.forEach(font => {
        css += '@font-face {\n';
        css += `  font-family: "${font['font-family']}";\n`;
        
        // Add src property with all URLs
        if (font.urls && font.urls.length > 0) {
          css += '  src: ';
          css += font.urls.map(url => {
            // Determine format based on file extension
            let format = '';
            if (url.endsWith('.woff2')) format = 'woff2';
            else if (url.endsWith('.woff')) format = 'woff';
            else if (url.endsWith('.ttf')) format = 'truetype';
            else if (url.endsWith('.otf')) format = 'opentype';
            else if (url.endsWith('.eot')) format = 'embedded-opentype';
            else if (url.endsWith('.svg')) format = 'svg';
            
            return format ? `url("${url}") format("${format}")` : `url("${url}")`;
          }).join(',\n       ');
          css += ';\n';
        }
        
        // Add other properties if they exist
        ['font-style', 'font-weight', 'font-stretch', 'unicode-range', 'font-feature-settings'].forEach(prop => {
          if (font[prop]) {
            css += `  ${prop}: ${font[prop]};\n`;
          }
        });
        
        css += '}\n\n';
      });
      
      return css;
    }
    
    const fontFaceCss = createFontFaceCss(fontsData);
    console.log(fontFaceCss);
})();