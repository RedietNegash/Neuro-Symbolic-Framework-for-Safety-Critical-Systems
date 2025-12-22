# setup_env.sh
#!/bin/bash

echo "🔧 Setting up Neuro-Symbolic Verification Framework with Gemini"


if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi


if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi


echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt


echo "🔑 Setting up environment variables..."


if [ ! -f .env ]; then
    cat > .env << EOF
# Google Gemini API Configuration
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-3-pro-preview

# Llama Configuration (via Ollama)
LLAMA_MODEL=llama3:8b
LLAMA_HOST=http://localhost:11434

# Verification Settings
MAX_ITERATIONS=5
VERIFICATION_TIMEOUT=30
EOF
    echo "Created .env file. Please update GEMINI_API_KEY with your actual key."
fi

echo "Setup complete!"
echo "Next steps:"
echo "   1. Get your Gemini API key from: https://aistudio.google.com/app/apikey"
# echo "   2. Update the GEMINI_API_KEY in the .env file"
echo "   2. For Llama: Install Ollama (curl -fsSL https://ollama.com/install.sh | sh) and pull model (ollama pull llama3:8b)"
echo "   3. Update .env file with your preferences (set ACTIVE_LLM to 'gemini' or 'llama')"
echo "   3. Run: python main.py"
