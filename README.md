# AutomaticEDA

An **LLM-powered agent EDA tool** for digital IC design.  Given a plain-text
specification of an integrated circuit, the agent automatically generates:

- **RTL** – synthesizable SystemVerilog source code
- **Testbench** – a self-checking SystemVerilog simulation testbench
- **SVA** – SystemVerilog Assertions for formal verification

---

## Features

| Artefact | File name | Description |
|---|---|---|
| RTL | `design.sv` | Synthesizable SystemVerilog module |
| Testbench | `tb_design.sv` | Self-checking simulation testbench |
| SVA | `design_sva.sv` | Formal-verification assertion module |

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

### Command-line interface

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

### Python API

```python
from eda_agent import EDAAgent
from eda_agent.utils.file_utils import save_results

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
```

---

## Project structure

```
AutomaticEDA/
├── main.py                          # CLI entry point
├── requirements.txt
├── setup.py
├── .env.example
├── eda_agent/
│   ├── agent.py                     # EDAAgent orchestrator & EDAResult dataclass
│   ├── llm_client.py                # OpenAI API wrapper
│   ├── generators/
│   │   ├── rtl_generator.py         # RTL generation
│   │   ├── testbench_generator.py   # Testbench generation
│   │   └── sva_generator.py         # SVA generation
│   ├── prompts/
│   │   ├── rtl_prompts.py
│   │   ├── testbench_prompts.py
│   │   └── sva_prompts.py
│   └── utils/
│       └── file_utils.py            # Write artefacts to disk
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

