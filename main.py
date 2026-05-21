#!/usr/bin/env python3
"""Command-line interface for the AutomaticEDA agent.

Usage examples::

    # Provide the IC specification as a command-line argument
    python main.py --spec "8-bit synchronous up-counter with synchronous reset"

    # Read the IC specification from a text file
    python main.py --spec-file spec.txt

    # Specify a custom output directory and model
    python main.py --spec "..." --output-dir ./my_design --model gpt-4o

    # Analyse an EDA simulation error log against RTL files in ./output
    python main.py --analyze-error "ERROR: ..." --rtl-dir ./output

    # Read the error log from a file
    python main.py --analyze-error-file sim.log --rtl-dir ./output
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from eda_agent import EDAAgent, ErrorLogAnalyzer
from eda_agent.utils.file_utils import save_results
from eda_agent.utils.rtl_searcher import collect_rtl_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eda_agent",
        description=(
            "AutomaticEDA – an LLM-powered agent that generates SystemVerilog "
            "RTL, testbench, and SVA from a plain-text IC specification, and "
            "analyzes EDA simulation error logs against RTL source files."
        ),
    )

    # ------------------------------------------------------------------ #
    # Mutually exclusive top-level modes                                   #
    # ------------------------------------------------------------------ #
    mode_group = parser.add_mutually_exclusive_group(required=True)

    # Design-generation mode
    mode_group.add_argument(
        "--spec",
        metavar="TEXT",
        help="IC specification as a string (generation mode).",
    )
    mode_group.add_argument(
        "--spec-file",
        metavar="FILE",
        type=Path,
        help="Path to a text file containing the IC specification (generation mode).",
    )

    # Error-log analysis mode
    mode_group.add_argument(
        "--analyze-error",
        metavar="LOG_TEXT",
        help="EDA simulation error log text to analyze (analysis mode).",
    )
    mode_group.add_argument(
        "--analyze-error-file",
        metavar="FILE",
        type=Path,
        help="Path to a file containing the EDA simulation error log (analysis mode).",
    )

    # ------------------------------------------------------------------ #
    # Shared options                                                       #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Analysis-mode options                                                #
    # ------------------------------------------------------------------ #
    parser.add_argument(
        "--rtl-dir",
        metavar="DIR",
        default="output",
        help=(
            "Directory to search for RTL source files (*.sv, *.v, *.svh, *.vh) "
            "during error-log analysis (default: ./output)."
        ),
    )

    return parser


def _run_generation(args: argparse.Namespace) -> int:
    """Execute the RTL/testbench/SVA generation pipeline."""
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

    agent = EDAAgent(model=args.model)
    result = agent.run(specification, verbose=not args.quiet)

    written = save_results(result, output_dir=args.output_dir)

    if not args.quiet:
        print("\nGenerated files:")
        for name, path in written.items():
            print(f"  {name:10s}  {path}")

    return 0


def _run_analysis(args: argparse.Namespace) -> int:
    """Execute the EDA error-log analysis pipeline."""
    # Resolve error log text
    if args.analyze_error:
        error_log = args.analyze_error
    else:
        log_path: Path = args.analyze_error_file
        if not log_path.is_file():
            print(f"Error: error log file not found: {log_path}", file=sys.stderr)
            return 1
        error_log = log_path.read_text(encoding="utf-8").strip()

    if not error_log:
        print("Error: error log must not be empty.", file=sys.stderr)
        return 1

    # Collect RTL files
    try:
        rtl_files = collect_rtl_files(args.rtl_dir)
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        if rtl_files:
            print(f"[EDA Analyzer] Found {len(rtl_files)} RTL file(s) in '{args.rtl_dir}'.")
        else:
            print(
                f"[EDA Analyzer] Warning: no RTL files found in '{args.rtl_dir}'. "
                "Analysis will proceed without RTL context.",
                file=sys.stderr,
            )

    analyzer = ErrorLogAnalyzer(model=args.model)

    if not args.quiet:
        print("[EDA Analyzer] Analyzing error log …")

    result = analyzer.analyze(error_log=error_log, rtl_files=rtl_files)

    print("\n" + "=" * 72)
    print(result.analysis)
    print("=" * 72)

    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    # Check API key (required for both modes)
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "Error: OPENAI_API_KEY environment variable is not set.\n"
            "Set it directly or add it to a .env file in the current directory.",
            file=sys.stderr,
        )
        return 1

    # Dispatch to the appropriate mode
    if args.analyze_error or args.analyze_error_file:
        return _run_analysis(args)
    return _run_generation(args)


if __name__ == "__main__":
    sys.exit(main())
