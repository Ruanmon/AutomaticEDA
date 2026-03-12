#!/usr/bin/env python3
"""Command-line interface for the AutomaticEDA agent.

Usage examples::

    # Provide the IC specification as a command-line argument
    python main.py --spec "8-bit synchronous up-counter with synchronous reset"

    # Read the IC specification from a text file
    python main.py --spec-file spec.txt

    # Specify a custom output directory and model
    python main.py --spec "..." --output-dir ./my_design --model gpt-4o
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from eda_agent import EDAAgent
from eda_agent.utils.file_utils import save_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eda_agent",
        description=(
            "AutomaticEDA – an LLM-powered agent that generates SystemVerilog "
            "RTL, testbench, and SVA from a plain-text IC specification."
        ),
    )

    spec_group = parser.add_mutually_exclusive_group(required=True)
    spec_group.add_argument(
        "--spec",
        metavar="TEXT",
        help="IC specification as a string.",
    )
    spec_group.add_argument(
        "--spec-file",
        metavar="FILE",
        type=Path,
        help="Path to a text file containing the IC specification.",
    )

    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default="output",
        help="Directory where generated files are written (default: ./output).",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model name to use (default: gpt-4o).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve specification text
    if args.spec:
        specification = args.spec
    else:
        spec_path: Path = args.spec_file
        if not spec_path.is_file():
            print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
            return 1
        specification = spec_path.read_text(encoding="utf-8").strip()

    if not specification:
        print("Error: specification must not be empty.", file=sys.stderr)
        return 1

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "Error: OPENAI_API_KEY environment variable is not set.\n"
            "Set it directly or add it to a .env file in the current directory.",
            file=sys.stderr,
        )
        return 1

    agent = EDAAgent(model=args.model)
    result = agent.run(specification, verbose=not args.quiet)

    written = save_results(result, output_dir=args.output_dir)

    if not args.quiet:
        print("\nGenerated files:")
        for name, path in written.items():
            print(f"  {name:10s}  {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
