from src.server import _json_message


class FakeMessage:
    role = "assistant"
    content = "hello"


def test_json_message_normalizes_typed_ollama_messages():
    assert _json_message(FakeMessage()) == {"role": "assistant", "content": "hello"}


def test_json_message_keeps_plain_dicts():
    message = {"role": "user", "content": "hi"}
    assert _json_message(message) is message