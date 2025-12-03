# Neuro-Symbolic UAV Framework - Phase 1

## LLM Ensemble with Z3 Pre-Check

### Overview
This is Phase 1 of the comprehensive neuro-symbolic verification framework for UAV mission-critical systems. This phase implements the LLM ensemble with Z3 pre-check selection as shown in the architecture diagram.

### Architecture

graph TB
    A[Natural Language Requirement + Safety Property ϕ] --> B{LLM Ensemble}
    
    subgraph "Parallel Generation"
        B1[Gemini-2.5-Flash] --> C1[Code Candidate 1]
        B2[Llama-3.8B] --> C2[Code Candidate 2]
    end
    
    C1 --> D[Z3 Pre-Check Engine]
    C2 --> D
    
    D --> E[Score & Validate]
    E --> F[Select Best Candidate ✓]
    F --> G[Verified Code Output]
    
    style F fill:#d4edda,stroke:#28a745
    style G fill:#d4edda,stroke:#28a745
## File Structure
```bash
neuro-symbolic-uav-framework/
│
├── README.mda
├── pyproject.toml
├── requirements.txt
├── .env.example
├── setup.sh
│
├── config/
│   ├── __init__.py
│   ├── settings.py           # ⬅️ NEW: Configuration management
│   └── llm_config.py         # ⬅️ NEW: LLM-specific settings
│
├── src/
│   ├── __init__.py
│   │
│   ├── llm_ensemble/         # ⬅️ WEEK 1 FOCUS
│   │   ├── __init__.py
│   │   ├── base_client.py    # ⬅️ NEW: Abstract base class
│   │   ├── gemini_client.py  # ⬅️ NEW: Gemini integration
│   │   ├── llama_client.py   # ⬅️ NEW: Llama integration
│   │   ├── ensemble_manager.py # ⬅️ NEW: Main ensemble logic
│   │   ├── prompt_strategies.py # ⬅️ NEW: Prompt templates
│   │   └── z3_pre_check.py   # ⬅️ NEW: Z3 quick checks
│   │
│   └── utils/
│       ├── __init__.py
│       └── logging_setup.py  # ⬅️ NEW: Logging configuration
│
├── tests/
│   ├── __init__.py
│   └── test_llm_ensemble.py  # ⬅️ NEW: Tests for Phase 1
│
├── examples/
│   ├── __init__.py
│   └── demo_ensemble.py      # ⬅️ NEW: Demo script
│
└── main.py                   # ⬅️ UPDATED: Main entry point
```

# ✨ Features
1. **Multi-LLM Ensemble**: Parallel generation from Gemini 2.5 Flash and Llama 3.1 70B
2. **Z3 Pre-Check**: Quick formal validation of generated code before selection
3. **Safety-Focused Prompts**: Templates for safety-critical code generation
4. **Refinement Loop**: Feedback mechanism for iterative improvement
5. **Comprehensive Logging**: Detailed logging for debugging and analysis

# Setup

## Installation

```bash
# Clone repository
git clone <repository-url>
cd neuro-symbolic-uav-framework

# Setup environment
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Usage 

1. Run demo:
```bash
python main.py --demo
```

2. Single verification:
```bash
python main.py --single
```
3. Batch verification:
```bash
python main.py --batch
```
