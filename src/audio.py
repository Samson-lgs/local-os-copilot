"""Optional local push-to-talk recording and Whisper transcription."""

import tempfile
from pathlib import Path

MODEL_SIZE = "base.en"


def transcribe_audio_file(audio_path: str | Path, model_size: str = MODEL_SIZE) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        return f"Error: Install faster-whisper to transcribe audio. Details: {error}"
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text or "Error: No speech was detected."
    except Exception as error:
        return f"Error: Local transcription failed. Details: {error}"


def record_and_transcribe(seconds: int = 8, model_size: str = MODEL_SIZE) -> str:
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError as error:
        return f"Error: Install sounddevice and soundfile for microphone input. Details: {error}"
    if not isinstance(seconds, int) or seconds < 1 or seconds > 30:
        return "Error: Recording duration must be between 1 and 30 seconds."
    try:
        sample_rate = 16_000
        recording = sd.rec(seconds * sample_rate, samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
            path = Path(temporary.name)
        sf.write(path, recording, sample_rate)
        try:
            return transcribe_audio_file(path, model_size)
        finally:
            path.unlink(missing_ok=True)
    except Exception as error:
        return f"Error: Microphone recording failed. Details: {error}"
