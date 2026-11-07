"""Optional offline Windows text-to-speech service."""

MAX_SPEECH_LENGTH = 4_000


def speak_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return "Error: Speech text cannot be empty."
    if len(text) > MAX_SPEECH_LENGTH:
        return "Error: Speech text is too long."
    try:
        import pyttsx3
    except ImportError as error:
        return f"Error: Install pyttsx3 for local speech output. Details: {error}"
    try:
        engine = pyttsx3.init()
        engine.say(text.strip())
        engine.runAndWait()
        engine.stop()
        return "Success: Response spoken locally."
    except Exception as error:
        return f"Error: Local speech failed. Details: {error}"
