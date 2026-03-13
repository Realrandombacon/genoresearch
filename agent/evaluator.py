"""
Result evaluator — scores and classifies tool outputs.
"""

import logging
from orchestrator.llm import chat

log = logging.getLogger("genoresearch.evaluator")


class ResultEvaluator:
    """Evaluates tool results for significance and decides next steps."""

    EVAL_PROMPT = (
        "You are a genomics result evaluator. Given the following tool output,\n"
        "assess its scientific significance and decide the next step.\n\n"
        "Score the result:\n"
        "  - SIGNIFICANCE: HIGH / MEDIUM / LOW / NOISE\n"
        "  - NOVELTY: LIKELY_NOVEL / KNOWN / UNCLEAR\n"
        "  - ACTION: INVESTIGATE_DEEPER / LOG_FINDING / DISMISS / CROSS_REFERENCE\n\n"
        "Be concise.\n"
    )

    def evaluate(self, tool_name: str, result: str) -> dict:
        """Evaluate a tool result and return structured assessment."""
        messages = [
            {"role": "system", "content": "You are a genomics result evaluator."},
            {"role": "user", "content": (
                f"{self.EVAL_PROMPT}\n"
                f"Tool: {tool_name}\n"
                f"Result:\n{result[:2000]}"
            )},
        ]

        response = chat(messages, temperature=0.2)
        log.info("Evaluated %s result", tool_name)

        # Parse structured response
        assessment = {
            "raw": response,
            "significance": _extract_field(response, "SIGNIFICANCE"),
            "novelty": _extract_field(response, "NOVELTY"),
            "action": _extract_field(response, "ACTION"),
        }
        return assessment


def _extract_field(text: str, field: str) -> str:
    """Extract a labeled field value from LLM response."""
    for line in text.split("\n"):
        if field in line.upper():
            parts = line.split(":")
            if len(parts) >= 2:
                return parts[-1].strip()
    return "UNKNOWN"
