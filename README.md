# NeuroVerify-Code: Neuro-Symbolic Verification of LLM-Generated Code

A closed-loop **Generate–Test–Critique–Refine** pipeline that combines LLM code
generation (Gemini / Llama) with formal verification via the **Z3 SMT solver** to
produce code that provably satisfies safety properties for safety-critical systems.

Accepted at PanAfriCon AI 2025.

## How It Works

1. A natural-language task is given to the LLM (Gemini-2.5-Flash / Llama-3-8B).
2. Generated Python code is parsed via the `ast` module into SMT-LIB constraints.
3. Z3 checks the negated safety property: if unsatisfiable, the property holds; if
   satisfiable, it returns a counterexample.
4. The counterexample is converted to natural-language feedback and fed back to the
   LLM, which refines its output. Steps repeat until verified or the iteration limit is reached.

## Results

Evaluated on four safety-critical scenarios (drone altitude, speed–obstacle,
robotic grasp, rotation limit), each run 20× to account for LLM non-determinism:

| Metric | LLM-only | NeuroVerify-Code |
|---|---|---|
| Logical consistency | 75% | **100%** |
| Boundary-condition accuracy | — | **+75%** |
| Conditional-logic accuracy | — | **+50%** |
| Mean refinement iterations | — | 1.2–1.25 |

## Repository Structure

​```
nurosymbolic/
├── main.py                          # Entry point
├── experiment_runner.py             # Runs the full benchmark evaluation
├── Generate-Test-Critique-Refine.py # Core refinement loop
├── llm_client.py                    # LLM provider interface (Gemini / Llama)
├── neuro_symbolic_verifier.py       # Verification orchestration
├── symbolic_bridge.py               # AST → symbolic representation
├── python_to_z3_converter.py        # SMT-LIB constraint generation
├── safety_specification.py          # Safety property definitions
├── gold_standard.py                 # Reference correct implementations
├── example_usage.py                 # Minimal usage example
├── natural_language_specifications.txt
├── requirements.txt
└── logs/
​```

## Installation

​```bash
git clone https://github.com/RedietNegash/Neuro-Symbolic-Framework-for-for-Safety-Critical-Systems.git
cd Neuro-Symbolic-Framework-for-for-Safety-Critical-Systems/nurosymbolic
pip install -r requirements.txt
​```

Then update `config.py` with your LLM provider (Gemini or Llama) and API credentials.

## Usage

​```bash
python main.py               # Run the pipeline on a single task
python experiment_runner.py  # Run the full benchmark evaluation
python example_usage.py      # Minimal example
​```

## Author

Rediet Negash Enyew

## License

MIT
