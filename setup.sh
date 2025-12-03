#!/bin/bash
echo "🔧 Setting up Neuro-Symbolic UAV Framework - Phase 1"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔑 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your API keys"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs artifacts/generated_code artifacts/verification_results

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your API keys"
echo "2. For Llama: Install Ollama and run: ollama pull llama3.1:70b"
echo "3. Run demo: python main.py --demo"
echo "4. Run tests: python -m pytest tests/"