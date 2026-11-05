import subprocess
import sys

import pyautogui

WINDOWS_APP_ALIASES = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "wordpad": "write.exe",
}
MAX_APP_NAME_LENGTH = 80
MAX_TYPED_TEXT_LENGTH = 4_000


def open_application(app_name: str) -> str:
    """
    Opens a standard desktop application by name.
    """
    if not isinstance(app_name, str):
        return "Error: Application name must be text."
    app_name = app_name.strip()
    if not app_name:
        return "Error: Application name cannot be empty."
    if len(app_name) > MAX_APP_NAME_LENGTH:
        return "Error: Application name is too long."
    if sys.platform == "win32" and app_name.casefold() not in WINDOWS_APP_ALIASES:
        return f"Error: '{app_name}' is not an allowed Windows application."

    try:
        if sys.platform == "win32":
            launch_name = WINDOWS_APP_ALIASES.get(app_name.casefold(), app_name)
            subprocess.Popen([launch_name])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])

        return f"Success: Opened {app_name}"

    except Exception as error:
        return f"Error: Failed to open {app_name}. Details: {error}"

def type_text(text: str) -> str:
    """
    Types the provided text directly into the active window.
    """
    if not isinstance(text, str):
        return "Error: Text must be a string."
    if not text:
        return "Error: Text cannot be empty."
    if len(text) > MAX_TYPED_TEXT_LENGTH:
        return "Error: Text is too long."

    try:
        pyautogui.write(text, interval=0.02)
        return "Success: Typed out the requested text."
    
    except Exception as error:
        return f"Error: Failed to type text. Details: {error}"