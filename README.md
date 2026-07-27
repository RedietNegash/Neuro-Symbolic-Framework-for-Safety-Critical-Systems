# Neuro-Symbolic Framework for Verifying LLM-Generated Code for Safety-Critical Systems

Iterative Generate–Test–Critique–Refine pipeline that combines LLM code generation (Gemini / Llama) with formal verification via the Z3 SMT Solver.

Accepted at PanAfriCon AI 2025.

# How It Works

Natural Language Task → LLM Code Generation → Python AST → SMT Constraints → Z3 Verification
                                                                                      │
                                                              Yes ◄── Verified? ──► No
                                                               │                     │
                                                        Verified Code       Counterexample → Critique → Refine → Repeat
# Repository Structure

nurosymbolic/
├── main.py
├── experiment_runner.py
├── Generate-Test-Critique-Refine.py
├── llm_client.py
├── neuro_symbolic_verifier.py
├── symbolic_bridge.py
├── python_to_z3_converter.py
├── safety_specification.py
├── gold_standard.py
├── natural_language_specifications.txt
├── logs/
├── requirements.txt
└── example_usage.py

# Installation

git clone https://github.com/RedietNegash/Neuro-Symbolic-Framework-for-for-Safety-Critical-Systems.git
cd Neuro-Symbolic-Framework-for-for-Safety-Critical-Systems/nurosymbolic
pip install -r requirements.txt
Update config.py with your LLM provider (Gemini or Llama) and API credentials.

# Usage

python main.py              
python experiment_runner.py 
python example_usage.py     

Author
Rediet Negash Enyew

License
MIT
