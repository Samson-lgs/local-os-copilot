from src.benchmark import BENCHMARK_PROMPTS, benchmark_model


class FakeClient:
    def chat(self, *, model, messages, tools):
        content = messages[0]["content"]
        if "read_screen" in content:
            return {"message": {"content": "tool requested", "tool_calls": [{"function": {"name": "read_screen"}}]}}
        return {"message": {"content": "local response"}}


def test_benchmark_measures_expected_tool_selection():
    result = benchmark_model(FakeClient(), "test-model", rounds=2)

    assert result.prompts == len(BENCHMARK_PROMPTS) * 2
    assert result.tool_call_requests == 2
    assert result.expected_tool_requests == 2
    assert result.correct_tool_selections == 4
    assert result.tool_call_accuracy == 1.0
    assert result.average_latency_ms >= 0