// AmiriFont.js - Save this in soap-recorder-frontend/src/fonts/AmiriFont.js
import { jsPDF } from "jspdf";

// This loads Amiri font dynamically from CDN
export const loadAmiriFont = async () => {
  try {
    const response = await fetch('https://cdn.jsdelivr.net/gh/alif-type/amiri@0.113/web/fonts/AmiriWeb-Regular.woff');
    const fontData = await response.arrayBuffer();
    
    // Convert to base64
    const base64 = btoa(String.fromCharCode(...new Uint8Array(fontData)));
    
    // Add to jsPDF
    const callAddFont = function() {
      this.addFileToVFS('Amiri-Regular.ttf', base64);
      this.addFont('Amiri-Regular.ttf', 'Amiri', 'normal');
    };
    
    jsPDF.API.events.push(['addFonts', callAddFont]);
    
    return true;
  } catch (error) {
    console.error('Failed to load Amiri font:', error);
    return false;
  }
};