"""
Main configuration settings for the neuro-symbolic framework
"""
import os
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Settings:
    """Global framework settings"""
    
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
    
    # LLM Settings
    LLM_TIMEOUT: int = 30  # seconds
    LLM_MAX_RETRIES: int = 3
    LLM_TEMPERATURE: float = 0.1  # Low temp for deterministic code gen
    
    # Ensemble Settings
    ENSEMBLE_MODELS: list = field(default_factory=lambda: ["gemini", "llama"])
    ENSEMBLE_PARALLEL: bool = True
    ENSEMBLE_MAX_WORKERS: int = 4
    
    # Z3 Pre-Check Settings
    Z3_PRECHECK_TIMEOUT: int = 5  # seconds for quick check
    Z3_PRECHECK_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """Create necessary directories"""
        self.LOG_DIR.mkdir(exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.ARTIFACTS_DIR / "generated_code").mkdir(exist_ok=True)
        (self.ARTIFACTS_DIR / "verification_results").mkdir(exist_ok=True)
    
    @property
    def gemini_api_key(self) -> str:
        """Get Gemini API key from environment"""
        key = os.getenv("GEMINI_API_KEY")
        if not key or key == "your-gemini-api-key-here":
            raise ValueError("GEMINI_API_KEY not set in .env file")
        return key
    
    @property
    def llama_endpoint(self) -> str:
        """Get Llama endpoint from environment"""
        return os.getenv("LLAMA_ENDPOINT", "http://localhost:11434")
    
    @property
    def llama_model(self) -> str:
        """Get Llama model name"""
        return os.getenv("LLAMA_MODEL", "llama3:8b")

# Global settings instance
settings = Settings()