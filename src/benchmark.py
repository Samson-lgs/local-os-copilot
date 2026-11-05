"""Measure local Ollama response latency and tool-call selection."""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import ollama

from src.main import TOOLS_SCHEMA
from src.settings import MODEL, OLLAMA_HOST, validate_local_endpoint

BENCHMARK_PROMPTS = (
    "Reply with one short sentence explaining what you can do.",
    "Use the read_screen tool to inspect the visible screen, then briefly describe the result.",
)


class ChatClient(Protocol):
    def chat(self, *, model: str, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> Any:
        ...


@dataclass(frozen=True)
class BenchmarkResult:
    model: str
    rounds: int
    prompts: int
    average_latency_ms: float
    tool_call_requests: int
    expected_tool_requests: int
    correct_tool_selections: int
    tool_call_accuracy: float


def benchmark_model(client: ChatClient, model: str, rounds: int = 1) -> BenchmarkResult:
    latencies: list[float] = []
    tool_call_requests = 0
    expected_tool_requests = rounds
    correct_tool_selections = 0
    for _ in range(rounds):
        for prompt in BENCHMARK_PROMPTS:
            started = time.perf_counter()
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                tools=TOOLS_SCHEMA,
            )
            latencies.append((time.perf_counter() - started) * 1000)
            message = response["message"]
            selected_tool = bool(message.get("tool_calls"))
            expected_tool = "read_screen" in prompt
            if selected_tool:
                tool_call_requests += 1
            if selected_tool == expected_tool:
                correct_tool_selections += 1
    total_requests = rounds * len(BENCHMARK_PROMPTS)
    return BenchmarkResult(
        model=model,
        rounds=rounds,
        prompts=total_requests,
        average_latency_ms=round(sum(latencies) / len(latencies), 2),
        tool_call_requests=tool_call_requests,
        expected_tool_requests=expected_tool_requests,
        correct_tool_selections=correct_tool_selections,
        tool_call_accuracy=round(correct_tool_selections / total_requests, 3),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local Ollama models without executing desktop tools.")
    parser.add_argument("--models", nargs="+", default=[MODEL], help="Installed local Ollama model names.")
    parser.add_argument("--rounds", type=int, default=1, help="Repetitions per prompt.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")
    validate_local_endpoint()
    client = ollama.Client(host=OLLAMA_HOST)
    results = [benchmark_model(client, model, args.rounds) for model in args.models]
    payload = [asdict(result) for result in results]
    print(json.dumps(payload, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            json.dump(payload, output, indent=2)


if __name__ == "__main__":
    main()