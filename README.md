# AutomaticEDA

An **LLM-powered agent EDA tool** for digital IC design.  Given a plain-text
specification of an integrated circuit, the agent automatically generates:

- **RTL** – synthesizable SystemVerilog source code
- **Testbench** – a self-checking SystemVerilog simulation testbench
- **SVA** – SystemVerilog Assertions for formal verification

It also includes an **Error Log Analyzer** plugin that takes an EDA simulation
error log, automatically searches RTL source files, and uses an LLM to identify
the root causes and suggest fixes.

---

## Features

| Artefact | File name | Description |
|---|---|---|
| RTL | `design.sv` | Synthesizable SystemVerilog module |
| Testbench | `tb_design.sv` | Self-checking simulation testbench |
| SVA | `design_sva.sv` | Formal-verification assertion module |

| Plugin | Description |
|---|---|
| Error Log Analyzer | Paste an EDA simulation error log → automatic RTL search + LLM root-cause analysis |

---

## Requirements

- Python ≥ 3.10
- An OpenAI-compatible API key (`OPENAI_API_KEY`)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Ruanmon/AutomaticEDA.git
cd AutomaticEDA

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your OpenAI API key:

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...
```

Alternatively, export the variable directly:

```bash
export OPENAI_API_KEY=sk-...
```

---

## Usage

### Command-line interface – Design Generation

```bash
# Inline specification
python main.py --spec "8-bit synchronous up-counter with synchronous active-high reset"

# Specification from a file
python main.py --spec-file my_spec.txt

# Custom output directory and model
python main.py --spec "..." --output-dir ./my_design --model gpt-4o
```

Generated files are written to `./output/` by default:

```
output/
├── design.sv       ← RTL
├── tb_design.sv    ← Testbench
└── design_sva.sv   ← SVA
```

### Command-line interface – Error Log Analysis

Paste (or redirect) an EDA simulation error log and point the tool at the RTL
directory to get an instant LLM-powered root-cause analysis:

```bash
# Pass the error log as a string
python main.py --analyze-error "ERROR: undeclared identifier 'cnt' ..." \
               --rtl-dir ./output

# Read the error log from a file (e.g. a VCS/ModelSim log)
python main.py --analyze-error-file sim.log --rtl-dir ./output

# Use a different model
python main.py --analyze-error-file sim.log --rtl-dir ./output --model gpt-4o
```

The analyzer will:
1. Scan `--rtl-dir` for all `*.sv`, `*.v`, `*.svh`, and `*.vh` files.
2. Send the error log **and** the RTL source to the LLM.
3. Print a structured report with:
   - **Error Summary** – every distinct error/warning.
   - **Root Cause Analysis** – traced to specific RTL files/signals.
   - **Suggested Fixes** – concrete code changes or configuration steps.

### Python API

```python
from eda_agent import EDAAgent, ErrorLogAnalyzer
from eda_agent.utils.file_utils import save_results
from eda_agent.utils.rtl_searcher import collect_rtl_files

# ── Design generation ──────────────────────────────────────────────────────
spec = """
4-bit synchronous up-counter with a synchronous active-high reset.
The counter increments on every rising clock edge when enable is high.
Ports: clk (input), rst (input), en (input), count[3:0] (output).
"""

agent = EDAAgent(model="gpt-4o")   # uses OPENAI_API_KEY from environment
result = agent.run(spec)

print(result.rtl)
print(result.testbench)
print(result.sva)

# Save all artefacts to disk
save_results(result, output_dir="output")

# ── Error log analysis ─────────────────────────────────────────────────────
error_log = """
ERROR: /path/to/design.sv:42: undeclared identifier 'cnt'
ERROR: /path/to/design.sv:55: port width mismatch (expected 4 bits, got 8)
"""

rtl_files = collect_rtl_files("output")   # scans ./output for *.sv / *.v files
analyzer = ErrorLogAnalyzer(model="gpt-4o")
analysis = analyzer.analyze(error_log=error_log, rtl_files=rtl_files)

print(analysis.analysis)   # structured root-cause report
```

---

## Project structure

```
AutomaticEDA/
├── main.py                              # CLI entry point
├── requirements.txt
├── setup.py
├── .env.example
├── eda_agent/
│   ├── agent.py                         # EDAAgent orchestrator & EDAResult dataclass
│   ├── llm_client.py                    # OpenAI API wrapper
│   ├── analyzers/
│   │   └── error_log_analyzer.py        # ErrorLogAnalyzer & ErrorAnalysisResult
│   ├── generators/
│   │   ├── rtl_generator.py             # RTL generation
│   │   ├── testbench_generator.py       # Testbench generation
│   │   └── sva_generator.py             # SVA generation
│   ├── prompts/
│   │   ├── rtl_prompts.py
│   │   ├── testbench_prompts.py
│   │   ├── sva_prompts.py
│   │   └── error_log_prompts.py         # Prompts for error-log analysis
│   └── utils/
│       ├── file_utils.py                # Write artefacts to disk
│       └── rtl_searcher.py              # Discover & load RTL source files
└── tests/
    └── test_eda_agent.py
```

---

## Running the tests

```bash
python -m pytest tests/ -v
```

No OpenAI API key is required to run the tests — all LLM calls are mocked.

---

## License

MIT

