"""
Tests for LLM Ensemble components (Phase 1)
"""
import unittest
from unittest.mock import Mock, patch
import tempfile
import os

from src.llm_ensemble.base_client import BaseLLMClient
from src.llm_ensemble.ensemble_manager import LLMEnsembleManager
from src.llm_ensemble.z3_pre_check import Z3PreChecker

class TestBaseLLMClient(unittest.TestCase):
    """Test base LLM client functionality"""
    
    def test_validate_response(self):
        client = BaseLLMClient.__new__(BaseLLMClient)
        client.model_name = "test"
        
        # Valid response
        valid_code = "def test():\n    return True"
        self.assertTrue(client.validate_response(valid_code))
        
        # Invalid response (no function)
        invalid_code = "print('hello')"
        self.assertFalse(client.validate_response(invalid_code))
        
        # Empty response
        self.assertFalse(client.validate_response(""))
    
    def test_get_stats(self):
        client = BaseLLMClient.__new__(BaseLLMClient)
        client.model_name = "test"
        client.request_count = 10
        client.total_tokens = 1000
        client.error_count = 2
        
        stats = client.get_stats()
        self.assertEqual(stats["model"], "test")
        self.assertEqual(stats["requests"], 10)
        self.assertAlmostEqual(stats["success_rate"], 0.8, places=2)

class TestZ3PreChecker(unittest.TestCase):
    """Test Z3 pre-check functionality"""
    
    def setUp(self):
        self.checker = Z3PreChecker(timeout_ms=1000)
    
    def test_validate_syntax(self):
        # Valid syntax
        valid_code = "def test(x):\n    return x > 0"
        valid, msg = self.checker.validate_syntax(valid_code)
        self.assertTrue(valid)
        
        # Invalid syntax
        invalid_code = "def test(x):\n    return x > "  # Incomplete
        valid, msg = self.checker.validate_syntax(invalid_code)
        self.assertFalse(valid)
        self.assertIn("Syntax error", msg)
    
    def test_check_banned_patterns(self):
        # Safe code
        safe_code = "def test():\n    return True"
        safe, issues = self.checker.check_banned_patterns(safe_code)
        self.assertTrue(safe)
        self.assertEqual(len(issues), 0)
        
        # Dangerous code with eval
        dangerous_code = "def test():\n    eval('print(1)')\n    return True"
        safe, issues = self.checker.check_banned_patterns(dangerous_code)
        self.assertFalse(safe)
        self.assertGreater(len(issues), 0)
    
    def test_quick_check_basic(self):
        # Test basic quick check
        code = "def check_altitude(altitude):\n    return altitude >= 40 and altitude <= 60"
        safety_property = "And(altitude >= 40, altitude <= 60)"
        variables = {"altitude": "real"}
        
        valid, score, diagnostic = self.checker.quick_check(
            code, safety_property, variables
        )
        
        self.assertTrue(valid)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertIsInstance(diagnostic, str)

class TestEnsembleManager(unittest.TestCase):
    """Test ensemble manager functionality"""
    
    @patch('src.llm_ensemble.ensemble_manager.GeminiClient')
    @patch('src.llm_ensemble.ensemble_manager.LlamaClient')
    def test_ensemble_initialization(self, mock_llama, mock_gemini):
        # Mock clients
        mock_gemini_instance = Mock()
        mock_gemini_instance.model_name = "gemini-mock"
        mock_gemini.return_value = mock_gemini_instance
        
        mock_llama_instance = Mock()
        mock_llama_instance.model_name = "llama-mock"
        mock_llama.return_value = mock_llama_instance
        
        # Create ensemble manager
        manager = LLMEnsembleManager()
        
        # Check models initialized
        self.assertIn("gemini", manager.models)
        self.assertIn("llama", manager.models)
    
    def test_select_best_candidate(self):
        manager = LLMEnsembleManager()
        
        # Test candidates
        candidates = [
            {'model': 'model1', 'code': 'def test1(): return True', 'z3_score': 0.8},
            {'model': 'model2', 'code': 'def test2(): return False', 'z3_score': 0.9},
            {'model': 'model3', 'code': 'def test3(): return None', 'z3_score': 0.7}
        ]
        
        # Test z3_weighted selection
        best = manager.select_best_candidate(candidates, method="z3_weighted")
        self.assertEqual(best['model'], 'model2')  # Highest score
        self.assertEqual(best['z3_score'], 0.9)
        
        # Test first_valid selection
        candidates_low = [
            {'model': 'model1', 'code': 'def test1(): return True', 'z3_score': 0.5},
            {'model': 'model2', 'code': 'def test2(): return False', 'z3_score': 0.9}
        ]
        
        best = manager.select_best_candidate(candidates_low, method="first_valid")
        self.assertEqual(best['model'], 'model2')  # First with score > 0.6

if __name__ == '__main__':
    unittest.main()