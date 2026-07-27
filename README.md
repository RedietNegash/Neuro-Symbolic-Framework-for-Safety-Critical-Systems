# NeuroVerify-Code: Neuro-Symbolic Verification of LLM-Generated Code

A closed-loop **Generate–Test–Critique–Refine** pipeline that combines LLM code generation (Gemini / Llama) with formal verification via the **Z3 SMT solver**, producing code that provably satisfies safety properties for safety-critical systems such as autonomous drones and robotics.

* Accepted at PanAfriCon AI 2025.

## How It Works

1. A natural-language task is given to the LLM (Gemini-2.5-Flash / Llama-3-8B), which generates Python code.
2. The generated code is parsed via Python's `ast` module and translated into SMT-LIB constraints.
3. Z3 checks the satisfiability of the *negated* safety property: if unsatisfiable, the property holds; if satisfiable, Z3 returns a counterexample.
4. The counterexample is converted into natural-language feedback and returned to the LLM, which refines its output.
5. Steps repeat until the code is verified or the maximum refinement limit is reached.

## Results

Evaluated on four safety-critical scenarios (drone altitude, speed–obstacle, robotic grasp, rotation limit), each run 20x to account for LLM non-determinism. Results shown per model (LLM-only vs. NeuroVerify-Code):

| Metric | Llama (LLM-only → NeuroVerify) | Gemini (LLM-only → NeuroVerify) |
|---|---|---|
| Logical consistency | 75% → **100%** | 75% → **100%** |
| Boundary-condition accuracy | 25% → **100%** | 25% → **100%** |
| Conditional-logic accuracy | 50% → **100%** | 50% → **100%** |
| Mean refinement iterations | 1.00 → 1.25 | 0.98 → 1.20 |

Across both models, NeuroVerify-Code reached 100% logical consistency versus 75% for the LLM-only baseline, with only ~1.2–1.25 refinement iterations on average.

## Repository Structure

```
nurosymbolic/
├── main.py                          ->  Entry point
├── experiment_runner.py             ->  Full benchmark evaluation
├── Generate-Test-Critique-Refine.py ->  Core refinement loop
├── llm_client.py                    ->  LLM provider interface (Gemini / Llama)
├── neuro_symbolic_verifier.py       ->  Verification orchestration
├── symbolic_bridge.py               -> AST to symbolic representation
├── python_to_z3_converter.py        ->  SMT-LIB constraint generation
├── safety_specification.py          ->  Safety property definitions
├── gold_standard.py                 ->  Reference correct implementations
├── example_usage.py                 ->  Minimal usage example
├── natural_language_specifications.txt
├── requirements.txt
└── logs/
```

## Installation

```bash
git clone https://github.com/RedietNegash/Neuro-Symbolic-Framework-for-Safety-Critical-Systems.git
cd Neuro-Symbolic-Framework-for-Safety-Critical-Systems/nurosymbolic
pip install -r requirements.txt
```

Then update `config.py` with your LLM provider (Gemini or Llama) and API credentials.

## Usage

```bash
python main.py               ->  Run the pipeline on a single task
python experiment_runner.py  ->  Run the full benchmark evaluation
python example_usage.py      ->  Minimal example
```

## Author

Rediet Negash Enyew

## License

MIT
