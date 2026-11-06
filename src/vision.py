import base64
import os
from io import BytesIO

import mss
import pytesseract
from PIL import Image

configured_tesseract = os.environ.get("TESSERACT_CMD")
standard_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if configured_tesseract:
    pytesseract.pytesseract.tesseract_cmd = configured_tesseract
elif os.path.exists(standard_tesseract):
    pytesseract.pytesseract.tesseract_cmd = standard_tesseract

def capture_screen() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")


def screenshot_base64() -> str:
    output = BytesIO()
    capture_screen().save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def screenshot_payload() -> dict[str, int | str]:
    image = capture_screen()
    output = BytesIO()
    image.save(output, format="PNG")
    return {"image": base64.b64encode(output.getvalue()).decode("ascii"), "width": image.width, "height": image.height}


def read_screen_region(left: int, top: int, width: int, height: int) -> str:
    if min(left, top, width, height) < 0 or width > 4_000 or height > 4_000:
        return "Error: Invalid screen region."
    try:
        text = pytesseract.image_to_string(capture_screen().crop((left, top, left + width, top + height)))
        return f"Success: Region text extracted:\n{text[:2000]}" if text.strip() else "Success: No readable text found in region."
    except Exception as error:
        return f"Error: Failed to read screen region. Details: {error}"


def read_screen() -> str:
    """
    Captures the main screen and extracts all readable text.
    """
    try:
        text = pytesseract.image_to_string(capture_screen())
        if not text.strip():
            return "Success: Screen read, but no readable text was found."
        return f"Success: Screen text extracted:\n{text[:2000]}"

    except Exception as error:
        return f"Error: Failed to read screen. Details: {error}"