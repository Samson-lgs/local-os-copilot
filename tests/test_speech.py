from src.speech import speak_text


def test_speech_rejects_empty_text():
    assert speak_text(" ").startswith("Error")


def test_speech_rejects_oversized_text():
    assert speak_text("x" * 4_001).startswith("Error")