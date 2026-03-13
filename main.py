"""
GenoResearch — Autonomous Genomics Research Agent
Entry point.

Usage:
    python main.py                              # Interactive mode
    python main.py --target "BRCA1 mutations"   # Target-specific
    python main.py --cycles 50                  # Long run
    python main.py --cycles 0                   # Infinite mode
    python main.py --plan                       # Planning mode only
    python main.py --lab-status                 # Check lab status
"""

import argparse
import traceback

from orchestrator import Orchestrator
from agent.planner import ResearchPlanner
from agent.memory import load_memory, save_memory
from agent.ui import C, log as ui_log
from lab.trainer import LabTrainer


def main():
    parser = argparse.ArgumentParser(description="GenoResearch — Autonomous Genomics Agent")
    parser.add_argument("--target", type=str, default=None,
                        help="Research target (e.g. 'BRCA1 mutations', 'p53 variants')")
    parser.add_argument("--cycles", type=int, default=0,
                        help="Max orchestrator cycles (0 = infinite, default)")
    parser.add_argument("--model", type=str, default=None,
                        help="Ollama model override (default: qwen3.5:4b)")
    parser.add_argument("--plan", action="store_true",
                        help="Planning mode — propose directions, don't execute")
    parser.add_argument("--lab-status", action="store_true",
                        help="Show ML lab experiment status")
    args = parser.parse_args()

    # Increment session counter
    memory = load_memory()
    memory["session_count"] = memory.get("session_count", 0) + 1
    save_memory(memory)

    if args.lab_status:
        trainer = LabTrainer()
        print(trainer.get_status())
        return

    if args.plan:
        planner = ResearchPlanner(memory)
        directions = planner.propose(focus=args.target)
        print(f"\n{C.BANNER}{C.BOLD}=== Research Directions ==={C.RESET}\n")
        print(directions)
        return

    # Main research loop
    try:
        orchestrator = Orchestrator(
            max_cycles=args.cycles,
            model=args.model,
            target=args.target,
        )
        orchestrator.run()
    except KeyboardInterrupt:
        ui_log("WARN", "Interrupted by user — saving memory...")
        save_memory(memory)
        print(f"\n{C.WARN}Session ended by user.{C.RESET}")
    except Exception:
        ui_log("ERROR", "Unexpected error:")
        traceback.print_exc()
        save_memory(memory)


if __name__ == "__main__":
    main()
