"""
run_antigravity.py
==================
CLI runner for Aisha's Antigravity queue worker.

Usage:
  python scripts/run_antigravity.py --once
  python scripts/run_antigravity.py --forever --poll 30
"""

import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.antigravity_agent import AntigravityAgent


def main():
    parser = argparse.ArgumentParser(description="Run Aisha Antigravity content queue worker")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job then exit")
    parser.add_argument("--forever", action="store_true", help="Run forever and poll for new jobs")
    parser.add_argument("--poll", type=int, default=30, help="Polling interval (seconds) for forever mode")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    agent = AntigravityAgent()

    if args.forever:
        agent.run_forever(args.poll)
        return

    output = agent.run_once()
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
