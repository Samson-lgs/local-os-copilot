from unittest.mock import Mock

from src import tools


def test_unknown_windows_application_is_rejected(monkeypatch):
    launcher = Mock()
    monkeypatch.setattr(tools.subprocess, "Popen", launcher)

    result = tools.open_application("cmd")

    assert result.startswith("Error:")
    launcher.assert_not_called()


def test_calculator_alias_launches_without_shell(monkeypatch):
    launcher = Mock()
    monkeypatch.setattr(tools.subprocess, "Popen", launcher)

    result = tools.open_application(" Calculator ")

    assert result == "Success: Opened Calculator"
    launcher.assert_called_once_with(["calc.exe"])


def test_type_text_rejects_empty_and_oversized_input(monkeypatch):
    typer = Mock()
    monkeypatch.setattr(tools.pyautogui, "write", typer)

    assert tools.type_text("").startswith("Error:")
    assert tools.type_text("x" * (tools.MAX_TYPED_TEXT_LENGTH + 1)).startswith("Error:")
    typer.assert_not_called()