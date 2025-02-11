(function () {
    /**
     * Returns an array of objects, each containing a FontFace (from document.fonts),
     * its font-family name, and an array of URLs (if any) that were specified in the src.
     */
    function listFontFacesAndURLs() {
      // Get all loaded FontFace objects.
      const fontFaces = Array.from(document.fonts).reduce((unique, face) => {
        const existing = unique.find(f => 
          f.family === face.family && 
          f.style === face.style && 
          f.weight === face.weight && 
          f.stretch === face.stretch
        );
        if (!existing) unique.push(face);
        return unique;
      }, []);
  
      // Gather all @font-face CSS rules from same-origin stylesheets.
      const fontFaceRules = [];
      for (const sheet of document.styleSheets) {
        try {
          // Some stylesheets (cross-origin, etc.) may not allow access.
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
  
      // For each FontFace from document.fonts, try to find the matching CSS rule
      // and extract its URL(s) from the src property.
      const result = fontFaces.map((ff) => {
        // Clean the font-family name (remove any quotes)
        const family = ff.family.replace(/["']/g, "").trim();
  
        // Look for a matching @font-face rule by comparing font-family names.
        const matchingRule = fontFaceRules.find((rule) => {
          const ruleFamily = rule.style
            .getPropertyValue("font-family")
            .replace(/["']/g, "")
            .trim();
          return ruleFamily === family;
        });
  
        let urls = [];
        if (matchingRule) {
          const src = matchingRule.style.getPropertyValue("src");
          // A regex to match any url(...) within the src string.
          const urlRegex = /url\(["']?([^"')]+)["']?\)/g;
          let match;
          while ((match = urlRegex.exec(src)) !== null) {
            urls.push(match[1]);
          }
        }
  
        return {
          fontFace: {
            family: ff.family,
            style: ff.style,
            weight: ff.weight,
            stretch: ff.stretch,
            status: ff.status,
            // loaded: ff.loaded,
            display: ff.display,
            ascentOverride: ff.ascentOverride,
            descentOverride: ff.descentOverride,
            featureSettings: ff.featureSettings,
            lineGapOverride: ff.lineGapOverride,
            sizeAdjust: ff.sizeAdjust,
            unicodeRange: ff.unicodeRange,
            variant: ff.variant
          },
          family,
          urls,
        };
      });
  
      return result.filter(item => item.urls.length > 0);
    }
  
    // Example usage: log the data structure to the console.
    const fontsData = listFontFacesAndURLs();
    console.log(fontsData);
  })();