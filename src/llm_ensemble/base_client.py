"""
Abstract base class for all LLM clients
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
import time

logger = logging.getLogger(__name__)

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        self.model_name = model_name
        self.config = config
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0
    
    @abstractmethod
    def generate_code(self, 
                     prompt: str, 
                     system_context: Optional[str] = None,
                     temperature: float = 0.1) -> str:
        """Generate code from prompt"""
        pass
    
    @abstractmethod
    def critique_code(self, 
                     code: str, 
                     requirements: str,
                     issues: List[str]) -> str:
        """Provide critique for code improvements"""
        pass
    
    @abstractmethod
    def naturalize_invariant(self, 
                           raw_invariant: str, 
                           context: str) -> str:
        """Convert formal invariant to natural language"""
        pass
    
    def validate_response(self, response: str) -> bool:
        """Basic validation of LLM response"""
        if not response or len(response.strip()) < 10:
            logger.warning(f"Empty or too short response from {self.model_name}")
            return False
        
        # Check for Python function definition
        if "def " not in response:
            logger.warning(f"No function definition in response from {self.model_name}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "model": self.model_name,
            "requests": self.request_count,
            "tokens": self.total_tokens,
            "errors": self.error_count,
            "success_rate": 1 - (self.error_count / max(self.request_count, 1))
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0