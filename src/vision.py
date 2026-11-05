import os

import mss
import pytesseract
from PIL import Image

configured_tesseract = os.environ.get("TESSERACT_CMD")
standard_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if configured_tesseract:
    pytesseract.pytesseract.tesseract_cmd = configured_tesseract
elif os.path.exists(standard_tesseract):
    pytesseract.pytesseract.tesseract_cmd = standard_tesseract

def read_screen() -> str:
    """
    Captures the main screen and extracts all readable text.
    """
    try:
        with mss.mss() as sct:
            # Capture the primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            
            # Convert to a format Tesseract can read
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Extract text
            text = pytesseract.image_to_string(img)
            
            if not text.strip():
                return "Success: Screen read, but no readable text was found."
                
            # Truncate if it's too long so we don't overwhelm the LLM's context window
            return f"Success: Screen text extracted:\n{text[:2000]}"
            
    except Exception as e:
        return f"Error: Failed to read screen. Details: {str(e)}"