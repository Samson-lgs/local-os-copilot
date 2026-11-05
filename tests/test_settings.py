import pytest

from src.settings import build_task_plan, should_offer_tools, trim_history, validate_local_endpoint


@pytest.mark.parametrize("host", ["http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434"])
def test_local_ollama_endpoints_are_allowed(host):
    assert validate_local_endpoint(host).startswith("http")


def test_remote_ollama_endpoint_is_rejected():
    with pytest.raises(ValueError, match="local endpoint"):
        validate_local_endpoint("https://example.com:11434")


def test_history_limit_preserves_system_message():
    messages = [{"role": "system", "content": "system"}]
    messages.extend({"role": "user", "content": str(index)} for index in range(10))

    trimmed = trim_history(messages, limit=4)

    assert len(trimmed) == 4
    assert trimmed[0]["role"] == "system"
    assert trimmed[-1]["content"] == "9"


def test_greeting_does_not_expose_desktop_tools():
    assert not should_offer_tools("hi")
    assert not should_offer_tools("What can you do?")


@pytest.mark.parametrize("prompt", ["read my screen", "search my docs", "open Calculator", "type hello"])
def test_explicit_action_exposes_tools(prompt):
    assert should_offer_tools(prompt)


def test_task_plan_describes_screen_and_document_work():
    plan = build_task_plan("Read my screen and search my docs")

    assert plan == ["Understand request", "Read visible screen", "Search local knowledge", "Verify result"]