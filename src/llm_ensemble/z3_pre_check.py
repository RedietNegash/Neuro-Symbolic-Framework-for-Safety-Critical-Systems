"""
Z3 Pre-Check module for quick validation of generated code
"""
import ast
import z3
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class Z3PreChecker:
    """Quick Z3-based validation of generated code"""
    
    def __init__(self, timeout_ms: int = 5000):
        self.timeout_ms = timeout_ms
        self.solver = z3.Solver()
        self.solver.set("timeout", timeout_ms)
    
    def quick_check(self, 
                   python_code: str, 
                   safety_property: str,
                   variables: Dict[str, str]) -> Tuple[bool, float, str]:
        """
        Perform quick Z3 check on generated code
        
        Returns: (is_valid, confidence_score, diagnostic_message)
        """
        try:
            # Parse Python code
            ast_tree = ast.parse(python_code)
            
            # Extract function and basic structure
            func_info = self._extract_function_info(ast_tree)
            if not func_info:
                return False, 0.0, "No valid function found"
            
            # Check variable usage matches specification
            var_match_score = self._check_variable_match(func_info["variables"], variables)
            
            # Quick Z3 consistency check
            z3_score, z3_diagnostic = self._z3_consistency_check(
                func_info, safety_property, variables
            )
            
            # Overall confidence score
            confidence = (var_match_score + z3_score) / 2.0
            
            diagnostic = f"Function: {func_info['name']}, Variables: {func_info['variables']}"
            if z3_diagnostic:
                diagnostic += f" | Z3: {z3_diagnostic}"
            
            return True, confidence, diagnostic
            
        except SyntaxError as e:
            return False, 0.0, f"Syntax error: {e}"
        except Exception as e:
            logger.error(f"Z3 pre-check error: {e}")
            return False, 0.0, f"Check error: {str(e)[:100]}"
    
    def _extract_function_info(self, ast_tree: ast.AST) -> Optional[Dict]:
        """Extract basic function information from AST"""
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.FunctionDef):
                # Get function name
                func_name = node.name
                
                # Get arguments
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                
                # Get return statements
                returns = []
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Return):
                        returns.append(ast.unparse(subnode) if hasattr(ast, 'unparse') else "return")
                
                # Get variables used
                variables = set()
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Name) and isinstance(subnode.ctx, ast.Load):
                        variables.add(subnode.id)
                
                return {
                    "name": func_name,
                    "args": args,
                    "returns": returns,
                    "variables": list(variables)
                }
        
        return None
    
    def _check_variable_match(self, 
                            code_vars: List[str], 
                            spec_vars: Dict[str, str]) -> float:
        """Check if code uses the specified variables"""
        if not spec_vars:
            return 1.0  # No specification variables
        
        spec_var_names = set(spec_vars.keys())
        code_var_set = set(code_vars)
        
        # Check overlap
        overlap = spec_var_names.intersection(code_var_set)
        
        if not overlap:
            return 0.0  # No overlap at all
        
        # Score based on coverage
        coverage = len(overlap) / len(spec_var_names)
        
        # Penalty for extra variables (might indicate misunderstanding)
        extra_vars = len(code_var_set - spec_var_names)
        penalty = min(0.2, extra_vars * 0.05)  # Small penalty for extra vars
        
        return max(0.0, coverage - penalty)
    
    def _z3_consistency_check(self, 
                            func_info: Dict, 
                            safety_property: str,
                            variables: Dict[str, str]) -> Tuple[float, str]:
        """
        Quick Z3 consistency check (not full verification)
        
        Returns: (score, diagnostic)
        """
        try:
            # Create Z3 variables based on specification
            z3_vars = {}
            for var_name, var_type in variables.items():
                if var_type == "int":
                    z3_vars[var_name] = z3.Int(var_name)
                elif var_type == "real":
                    z3_vars[var_name] = z3.Real(var_name)
                elif var_type == "bool":
                    z3_vars[var_name] = z3.Bool(var_name)
                else:
                    z3_vars[var_name] = z3.Real(var_name)  # Default
            
            # Try to parse the safety property
            try:
                property_expr = eval(safety_property, {}, z3_vars)
            except:
                # If property can't be parsed, assume it's valid
                return 0.5, "Property parsing skipped"
            
            # Quick check: property shouldn't be trivially false
            self.solver.push()
            self.solver.add(z3.Not(property_expr))
            
            result = self.solver.check()
            self.solver.pop()
            
            if result == z3.unsat:
                # Property is always true (tautology) - might be trivial
                return 0.7, "Property is tautological"
            elif result == z3.sat:
                # Property can be false (non-trivial) - good!
                return 0.9, "Property is non-trivial"
            else:
                return 0.5, "Z3 timeout or unknown"
                
        except Exception as e:
            logger.debug(f"Z3 consistency check failed: {e}")
            return 0.3, f"Z3 check error: {str(e)[:50]}"
    
    def validate_syntax(self, code: str) -> Tuple[bool, str]:
        """Basic syntax validation"""
        try:
            ast.parse(code)
            return True, "Syntax OK"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
    
    def check_banned_patterns(self, code: str) -> Tuple[bool, List[str]]:
        """Check for banned or dangerous patterns"""
        banned_patterns = [
            ("eval(", "eval function"),
            ("exec(", "exec function"),
            ("__import__", "dynamic import"),
            ("input()", "interactive input"),
            ("open(", "file operations"),
            ("os.system", "system calls"),
            ("subprocess", "subprocess calls")
        ]
        
        issues = []
        for pattern, description in banned_patterns:
            if pattern in code:
                issues.append(f"Contains {description}: {pattern}")
        
        return len(issues) == 0, issues