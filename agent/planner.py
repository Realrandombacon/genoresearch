"""
Research planner — proposes next research directions based on memory state.
"""

import logging

from agent.memory import summarize_memory
from orchestrator.llm import chat

log = logging.getLogger("genoresearch.planner")


class ResearchPlanner:
    """Uses the LLM to propose research directions."""

    PLANNING_PROMPT = (
        "You are a genomics research planner. Based on the current research state,\n"
        "propose the TOP 3 most promising next research directions.\n"
        "For each, explain:\n"
        "  1. What to investigate\n"
        "  2. Which tools/databases to use\n"
        "  3. What would constitute a novel finding\n"
        "  4. Estimated complexity (low/medium/high)\n\n"
        "Focus on areas NOT yet explored. Prioritize novelty and feasibility.\n"
    )

    def __init__(self, memory: dict):
        self.memory = memory

    def propose(self, focus: str = None) -> str:
        """Ask the LLM to propose next research directions."""
        context = summarize_memory(self.memory)
        user_msg = self.PLANNING_PROMPT + f"\nCurrent state:\n{context}"

        if focus:
            user_msg += f"\n\nUser wants to focus on: {focus}"

        messages = [
            {"role": "system", "content": "You are a genomics research planning assistant."},
            {"role": "user", "content": user_msg},
        ]

        response = chat(messages, temperature=0.8)
        log.info("Planner proposed directions")
        return response

    def evaluate_novelty(self, finding_title: str, finding_desc: str) -> str:
        """Ask the LLM whether a finding is likely novel."""
        messages = [
            {"role": "system", "content": "You are a genomics novelty evaluator."},
            {"role": "user", "content": (
                f"Is this finding likely novel or already well-known?\n\n"
                f"Title: {finding_title}\n"
                f"Description: {finding_desc}\n\n"
                f"Rate novelty: HIGH / MEDIUM / LOW and explain briefly."
            )},
        ]
        return chat(messages, temperature=0.3)
