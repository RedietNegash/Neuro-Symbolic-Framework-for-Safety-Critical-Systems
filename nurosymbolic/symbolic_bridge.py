# symbolic_bridge.py - FIXED VERSION

import ast
from z3 import *
from typing import Dict, Any

class ASTToZ3Translator(ast.NodeVisitor):
    """
    Translates Python AST to Z3 expressions for formal verification
    """
    
    def __init__(self, z3_vars=None):
        self.z3_vars = z3_vars if z3_vars is not None else {}
        self.result_expr = None
    
    def python_code_to_z3(self, python_code: str, z3_vars=None):
        """
        Main entry point: Convert Python function code to Z3 expression
        z3_vars: Dictionary of pre-created Z3 variables to use (CRITICAL!)
        """
        # Use provided variables if given - THIS IS THE KEY FIX
        if z3_vars is not None:
            self.z3_vars = z3_vars.copy()
            
        try:
            # Parse the Python code
            tree = ast.parse(python_code)
            
            # Find the function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_def = node
                    break
            
            if not func_def:
                print("DEBUG: No function definition found")
                return BoolVal(True)
            
            # ONLY create variables if they don't already exist
            for arg in func_def.args.args:
                var_name = arg.arg
                if var_name not in self.z3_vars:
                    # Determine type based on name
                    if any(keyword in var_name.lower() for keyword in ['initiated', 'is_', 'enabled', 'active']):
                        self.z3_vars[var_name] = Bool(var_name)
                    else:
                        self.z3_vars[var_name] = Real(var_name)
                    print(f"DEBUG: Created new variable {var_name} (type: {type(self.z3_vars[var_name])})")
            
            # Process the function body - find the return statement
            if func_def.body:
                for stmt in func_def.body:
                    result = self._process_statement(stmt)
                    # If we found a return statement, use it
                    if not (isinstance(result, BoolRef) and result.eq(BoolVal(True))):
                        print(f"DEBUG: Translation result type: {type(result)}")
                        print(f"DEBUG: Translation result: {result}")
                        return result
                    # For Return statements specifically
                    if isinstance(stmt, ast.Return):
                        print(f"DEBUG: Translation result type: {type(result)}")
                        print(f"DEBUG: Translation result: {result}")
                        return result
            
            return BoolVal(True)
            
        except Exception as e:
            print(f"DEBUG: Translation error: {e}")
            import traceback
            traceback.print_exc()
            return BoolVal(True)
    
    def _process_statement(self, stmt):
        """Process a statement node"""
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return BoolVal(True)
            return self._process_expression(stmt.value)
        elif isinstance(stmt, ast.If):
            return self._process_if(stmt)
        else:
            print(f"DEBUG: Unhandled statement type: {type(stmt)}")
            return BoolVal(True)
    
    def _process_if(self, if_node):
        """
        Convert if-statement to Z3 If expression
        Example: if distance < 20: return speed <= 10; else: return True
        Becomes: If(distance < 20, speed <= 10, True)
        """
        condition = self._process_expression(if_node.test)
        
        then_value = BoolVal(True)
        if if_node.body:
            for stmt in if_node.body:
                if isinstance(stmt, ast.Return):
                    then_value = self._process_expression(stmt.value)
                    break
        
        else_value = BoolVal(True)
        if if_node.orelse:
            for stmt in if_node.orelse:
                if isinstance(stmt, ast.Return):
                    else_value = self._process_expression(stmt.value)
                    break
                elif isinstance(stmt, ast.If):
                    else_value = self._process_if(stmt)
                    break
        
        return If(condition, then_value, else_value)
    
    def _process_expression(self, expr):
        """Process an expression node"""
        if expr is None:
            return BoolVal(True)
        
        # Handle boolean/numeric constants
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, bool):
                return BoolVal(expr.value)
            elif isinstance(expr.value, (int, float)):
                return RealVal(expr.value)
            else:
                return BoolVal(True)
        
        # Handle Name (variable reference) - CRITICAL PATH
        elif isinstance(expr, ast.Name):
            var_name = expr.id
            if var_name in self.z3_vars:
                return self.z3_vars[var_name]
            else:
                print(f"DEBUG: Variable {var_name} not found in z3_vars!")
                # Create the variable if it doesn't exist
                if any(keyword in var_name.lower() for keyword in ['initiated', 'is_', 'enabled', 'active']):
                    self.z3_vars[var_name] = Bool(var_name)
                else:
                    self.z3_vars[var_name] = Real(var_name)
                return self.z3_vars[var_name]
        
        # Handle comparison operators
        elif isinstance(expr, ast.Compare):
            return self._process_compare(expr)
        
        # Handle boolean operators (and, or, not)
        elif isinstance(expr, ast.BoolOp):
            return self._process_boolop(expr)
        
        # Handle unary operators (not)
        elif isinstance(expr, ast.UnaryOp):
            return self._process_unaryop(expr)
        
        # Default
        else:
            print(f"DEBUG: Unhandled expression type: {type(expr)}")
            return BoolVal(True)
    
    def _process_compare(self, compare_node):
        """
        Process comparison operations
        Example: distance < 20, speed <= 10
        """
        left = self._process_expression(compare_node.left)
        
        # Handle multiple comparisons (e.g., a < b < c)
        if len(compare_node.ops) == 1:
            op = compare_node.ops[0]
            right = self._process_expression(compare_node.comparators[0])
            
            if isinstance(op, ast.Lt):
                return left < right
            elif isinstance(op, ast.LtE):
                return left <= right
            elif isinstance(op, ast.Gt):
                return left > right
            elif isinstance(op, ast.GtE):
                return left >= right
            elif isinstance(op, ast.Eq):
                return left == right
            elif isinstance(op, ast.NotEq):
                return left != right
        
        # Handle chained comparisons
        else:
            conditions = []
            current_left = left
            for op, comparator in zip(compare_node.ops, compare_node.comparators):
                current_right = self._process_expression(comparator)
                
                if isinstance(op, ast.Lt):
                    conditions.append(current_left < current_right)
                elif isinstance(op, ast.LtE):
                    conditions.append(current_left <= current_right)
                elif isinstance(op, ast.Gt):
                    conditions.append(current_left > current_right)
                elif isinstance(op, ast.GtE):
                    conditions.append(current_left >= current_right)
                elif isinstance(op, ast.Eq):
                    conditions.append(current_left == current_right)
                elif isinstance(op, ast.NotEq):
                    conditions.append(current_left != current_right)
                
                current_left = current_right
            
            return And(*conditions)
        
        return BoolVal(True)
    
    def _process_boolop(self, boolop_node):
        """Process boolean operations (and, or)"""
        values = [self._process_expression(v) for v in boolop_node.values]
        
        if isinstance(boolop_node.op, ast.And):
            return And(*values)
        elif isinstance(boolop_node.op, ast.Or):
            return Or(*values)
        
        return BoolVal(True)
    
    def _process_unaryop(self, unaryop_node):
        """Process unary operations (not)"""
        operand = self._process_expression(unaryop_node.operand)
        
        if isinstance(unaryop_node.op, ast.Not):
            return Not(operand)
        
        return operand