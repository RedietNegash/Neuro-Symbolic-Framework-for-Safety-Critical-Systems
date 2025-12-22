# Neuro-Symbolic Framework for Safety-Critical Systems
## Overview
This project implements a neuro-symbolic verification framework that integrates large language models (LLMs) with formal verification using the Z3 theorem prover to ensure safety-critical systems meet specified requirements. It supports two LLMs: Google Gemini (cloud-based) and Llama 3 (local via Ollama), enabling flexible code generation and refinement for safety specifications.
The framework verifies safety properties for systems like drones and robotic arms, generating Python code that adheres to formal specifications and iteratively refining it based on Z3 counterexamples. This README provides detailed setup and usage instructions, with a focus on setting up and running Llama 3 locally using Ollama, alongside Gemini support.

## Features

- **Dual LLM Support**: Use Google Gemini or Llama 3 (via Ollama) for code generation.
- **Formal Verification**: Integrates Z3 to verify generated code against safety specifications.
- **Iterative Refinement**: Refines code using LLM feedback and Z3 counterexamples.
- **Safety Specifications**: Includes examples for drone altitude and robotic arm grasping.
.

## Prerequisites

### System Requirements:
- Ubuntu (tested on 22.04/24.04) with 16GB RAM (Llama 3 8B requires ~8GB).
- Optional: GPU (NVIDIA/AMD) for faster Llama 3 inference.


## Software:
- Python 3.8+ (3.12 recommended).


# Setup Instructions
1. Clone the Repository
```bash 
git clone <repository-url>
cd Neuro-Symbolic-Framework-for-for-Safety-Critical-Systems/nurosymbolic
```
2. Set Up Virtual Environment
```bash python3 -m venv nurosymbolic
source nurosymbolic/bin/activate
```
3. Install Dependencies

```bash 
pip install -r requirements.txt
```

4. Configure Environment Variables
- Create a .env file in the project root:
```bash nano .env ```

- Add:
```bash
# Google Gemini API Configuration
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# Llama Configuration (via Ollama)
LLAMA_MODEL=llama3:8b
LLAMA_HOST=http://localhost:11434

# Select active LLM (gemini or llama)
ACTIVE_LLM=llama

# Verification Settings
MAX_ITERATIONS=5
VERIFICATION_TIMEOUT=30
```

- Gemini API Key: Obtain from Google AI Studio.
- Llama 3: Uses local Ollama server; no API key needed.
- ACTIVE_LLM: Set to gemini or llama to choose the LLM backend.

5. Set Up Llama 3 Locally with Ollama
Llama 3 runs locally via the Ollama server, leveraging your 16GB RAM for efficient processing. Follow these steps to set up and start Llama 3 before running the framework.
 - Step 5.1: Install Ollama
  
  Install Ollama on your Ubuntu system:
```bash curl -fsSL https://ollama.com/install.sh | sh ```

 Verify installation:
```bash ollama --version ```

 - Step 5.2: Pull Llama 3 Model
Download the Llama 3 8B model (requires ~8GB storage and RAM):
ollama pull llama3:8b

Verify the model is available:
```bash ollama list ```

Expected output:
```bash NAME            ID              SIZE    MODIFIED
llama3:8b       <model-id>      8.0 GB  <timestamp>
```
- Step 5.3: Start Ollama Server
Start the Ollama server before running the framework:
```bash ollama serve ```

This runs in the foreground. To run in the background:
ollama serve &

Verify the server is running:
```bash curl http://localhost:11434 ```



```bash
ollama run llama3:8b

```
```bash
ollama run deepseek-coder:1.3b
```

## Run Project



```bash python3 main.py ```

