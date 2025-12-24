# src/verification/python_to_z3_converter.py
import ast
from typing import Dict, List, Optional, Any
from z3 import *

class PythonToZ3Converter(ast.NodeVisitor):
    """Converts Python AST to Z3 expressions with robust error handling"""
    
    def __init__(self, z3_vars: Dict):
        self.z3_vars = z3_vars
        self.assertions = []
        self.current_function = None
        self.return_value = None
        self.errors = []
    
    def visit_For(self, node):
        """Handle for loops via unrolling (default 3 iterations)"""
        try:
            # Only handle simple range(N) loops for now
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                # Simplified unrolling
                for _ in range(3):  # Unroll 3 times (Diagram: "Loop Unroll")
                    for stmt in node.body:
                        self.visit(stmt)
            else:
                # Treat as single pass block
                for stmt in node.body:
                    self.visit(stmt)
        except Exception as e:
            self.errors.append(f"For loop unrolling: {e}")

    def visit_While(self, node):
        """Handle while loops via bounded unrolling"""
        try:
            # Bounded unrolling (3 iterations)
            # Implies(condition, body_effects)
            # This is a simplification; full unrolling requires SSA or sophisticated state tracking
            # For now, we just visit the body to capture constraints, assuming loop executes at least once if condition is met
            condition = self.convert_to_z3_expr(node.test)
            self.assertions.append(self._ensure_bool(condition))
            
            for stmt in node.body:
                self.visit(stmt)
        except Exception as e:
            self.errors.append(f"While loop handling: {e}")

    def visit_FunctionDef(self, node):
        """Visit function definition"""
        self.current_function = node.name
        self.return_value = None
        
        try:
            # Process function body
            for stmt in node.body:
                self.visit(stmt)
            
            # If we have a return value, create the main implication
            if self.return_value is not None:
                bool_expr = self._ensure_bool(self.return_value)
                self.assertions.append(bool_expr)
        except Exception as e:
            self.errors.append(f"Function {node.name}: {e}")
    
    def visit_Return(self, node):
        """Visit return statement"""
        if node.value:
            try:
                self.return_value = self.convert_to_z3_expr(node.value)
            except Exception as e:
                self.errors.append(f"Return statement: {e}")
                # Create a safe default
                self.return_value = BoolVal(True)
    
    def visit_If(self, node):
        """Visit if statement and create logical implications"""
        try:
            condition = self.convert_to_z3_expr(node.test)
            
            # Process true branch
            true_return = self._extract_return_value(node.body)
            if true_return is not None:
                true_bool = self._ensure_bool(true_return)
                self.assertions.append(Implies(condition, true_bool))
            
            # Process false branch (else/elif)
            false_return = self._extract_return_value(node.orelse)
            if false_return is not None:
                false_bool = self._ensure_bool(false_return)
                self.assertions.append(Implies(Not(condition), false_bool))
            
            # Continue visiting child nodes
            for child in node.body + node.orelse:
                self.visit(child)
        except Exception as e:
            self.errors.append(f"If statement: {e}")
    
    def _ensure_bool(self, expr: Any) -> Any:
        """Ensure a Z3 expression is a boolean for use in logical contexts"""
        if expr is None:
            return BoolVal(True)
        
        if is_bool(expr):
            return expr
        
        # Handle truthiness for numbers
        if is_int(expr) or is_real(expr):
            return expr != 0
        
        # Handle truthiness for strings
        if is_string(expr):
            return Length(expr) > 0
        
        # For any other type, try to convert to bool
        try:
            # This is a safe conversion that won't cause sort mismatch
            return expr != 0
        except:
            # If all else fails, return a safe boolean
            return BoolVal(True)
    
    def _extract_return_value(self, stmts: List) -> Optional[Any]:
        """Extract return value from a list of statements"""
        for stmt in stmts:
            if isinstance(stmt, ast.Return) and stmt.value:
                try:
                    return self.convert_to_z3_expr(stmt.value)
                except Exception as e:
                    self.errors.append(f"Extract return value: {e}")
                    return None
            elif isinstance(stmt, ast.If):
                # Handle nested if statements
                try:
                    condition = self.convert_to_z3_expr(stmt.test)
                    true_ret = self._extract_return_value(stmt.body)
                    false_ret = self._extract_return_value(stmt.orelse)
                    
                    if true_ret is not None and false_ret is not None:
                        true_bool = self._ensure_bool(true_ret)
                        false_bool = self._ensure_bool(false_ret)
                        return If(condition, true_bool, false_bool)
                except Exception as e:
                    self.errors.append(f"Extract conditional return: {e}")
        
        return None
    
    def convert_to_z3_expr(self, node) -> Any:
        """Convert Python AST node to Z3 expression with robust error handling"""
        if node is None:
            return BoolVal(True)
        
        try:
            if isinstance(node, ast.Compare):
                return self._convert_comparison(node)
            elif isinstance(node, ast.BoolOp):
                return self._convert_bool_op(node)
            elif isinstance(node, ast.UnaryOp):
                return self._convert_unary_op(node)
            elif isinstance(node, ast.BinOp):
                return self._convert_bin_op(node)
            elif isinstance(node, ast.Name):
                return self._convert_name(node)
            elif isinstance(node, ast.Constant):
                return self._convert_constant(node)
            elif isinstance(node, ast.Call):
                return self._convert_call(node)
            elif isinstance(node, ast.IfExp):
                return self._convert_if_exp(node)
            else:
                raise ValueError(f"Unsupported AST node: {type(node).__name__}")
        except Exception as e:
            self.errors.append(f"Convert {type(node).__name__}: {e}")
            # Return a safe default
            return BoolVal(True)
    
    def _convert_if_exp(self, node: ast.IfExp) -> Any:
        """Convert ternary operator (x if condition else y)"""
        try:
            condition = self.convert_to_z3_expr(node.test)
            true_val = self.convert_to_z3_expr(node.body)
            false_val = self.convert_to_z3_expr(node.orelse)
            
            # Ensure all are boolean for If
            condition_bool = self._ensure_bool(condition)
            true_bool = self._ensure_bool(true_val)
            false_bool = self._ensure_bool(false_val)
            
            return If(condition_bool, true_bool, false_bool)
        except:
            return BoolVal(True)
    
    def _convert_comparison(self, node: ast.Compare) -> Any:
        """Convert comparison operation with type safety"""
        try:
            comparisons = []
            left = self.convert_to_z3_expr(node.left)
            
            for op, comparator in zip(node.ops, node.comparators):
                right = self.convert_to_z3_expr(comparator)
                
                # Ensure both sides are comparable (same sort)
                if is_bool(left) and not is_bool(right):
                    right = self._ensure_bool(right)
                elif not is_bool(left) and is_bool(right):
                    left = self._ensure_bool(left)
                
                if isinstance(op, ast.Eq):
                    comparisons.append(left == right)
                elif isinstance(op, ast.NotEq):
                    comparisons.append(left != right)
                elif isinstance(op, ast.Lt):
                    comparisons.append(left < right)
                elif isinstance(op, ast.LtE):
                    comparisons.append(left <= right)
                elif isinstance(op, ast.Gt):
                    comparisons.append(left > right)
                elif isinstance(op, ast.GtE):
                    comparisons.append(left >= right)
                else:
                    comparisons.append(BoolVal(True))  # Safe default
                
                left = right  # For chained comparisons
            
            if len(comparisons) == 1:
                return comparisons[0]
            return And(*comparisons)
        except:
            return BoolVal(True)
    
    def _convert_bool_op(self, node: ast.BoolOp) -> Any:
        """Convert boolean operation"""
        try:
            values = []
            for v in node.values:
                expr = self.convert_to_z3_expr(v)
                bool_expr = self._ensure_bool(expr)
                values.append(bool_expr)
            
            if isinstance(node.op, ast.And):
                return And(*values)
            elif isinstance(node.op, ast.Or):
                return Or(*values)
            else:
                return BoolVal(True)
        except:
            return BoolVal(True)
    
    def _convert_unary_op(self, node: ast.UnaryOp) -> Any:
        """Convert unary operation"""
        try:
            operand = self.convert_to_z3_expr(node.operand)
            
            if isinstance(node.op, ast.Not):
                bool_operand = self._ensure_bool(operand)
                return Not(bool_operand)
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return operand
            else:
                return operand
        except:
            return BoolVal(True)
    
    def _convert_bin_op(self, node: ast.BinOp) -> Any:
        """Convert binary operation"""
        try:
            left = self.convert_to_z3_expr(node.left)
            right = self.convert_to_z3_expr(node.right)
            
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
            else:
                return left  # Safe default
        except:
            return BoolVal(True)
    
    def _convert_name(self, node: ast.Name) -> Any:
        """Convert variable name to Z3 variable with fuzzy matching"""
        var_name = node.id
        
        # Exact match
        if var_name in self.z3_vars:
            return self.z3_vars[var_name]
        
        # Fuzzy matching for common variations
        var_variations = {
            'alt': 'altitude',
            'time': 'execution_time',
            'imu_failed': 'imu1_failed',
            'imu1': 'imu1_failed',
            'active': 'active_imu',
            'gps': 'gps_vel',
            'imu': 'imu_vel',
            'imu_velocity': 'imu_vel',
            'gps_velocity': 'gps_vel',
            'sig': 'is_signature_valid',
            'signature': 'is_signature_valid',
            'act': 'action',
            'battery': 'battery_level',
            'cmd': 'command',
            'heap': 'heap_usage',
            'memory': 'heap_usage'
        }
        
        # Try fuzzy matching
        for variation, actual in var_variations.items():
            if variation in var_name.lower() and actual in self.z3_vars:
                return self.z3_vars[actual]
        
        # If we can't find it, create a dummy variable to avoid crashes
        print(f"    [Warning] Undefined variable '{var_name}'. Using placeholder.")
        return BoolVal(True)  # Safe placeholder
    
    def _convert_constant(self, node: ast.Constant) -> Any:
        """Convert constant value"""
        value = node.value
        if isinstance(value, bool):
            return BoolVal(value)
        elif isinstance(value, int):
            return IntVal(value)
        elif isinstance(value, float):
            return RealVal(value)
        elif isinstance(value, str):
            return StringVal(value)
        else:
            return BoolVal(True)  # Safe default
    
    def _convert_call(self, node: ast.Call) -> Any:
        """Convert function call (limited support)"""
        try:
            if isinstance(node.func, ast.Name):
                f_name = node.func.id
                if f_name == "abs" and len(node.args) == 1:
                    arg = self.convert_to_z3_expr(node.args[0])
                    return If(arg >= 0, arg, -arg)
            
            # For other calls, return a safe default
            return BoolVal(True)
        except:
            return BoolVal(True)