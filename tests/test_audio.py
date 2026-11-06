from src.audio import record_and_transcribe


def test_recording_rejects_invalid_duration():
    assert record_and_transcribe(0).startswith("Error")
    assert record_and_transcribe(31).startswith("Error")
