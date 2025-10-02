# python_to_z3_converter.py
import ast
from typing import Dict, List, Optional, Any
from z3 import *

class PythonToZ3Converter(ast.NodeVisitor):
    """Converts Python AST to Z3 expressions"""
    
    def __init__(self, z3_vars: Dict):
        self.z3_vars = z3_vars
        self.assertions = []
        self.current_function = None
        self.return_value = None
    
    def visit_FunctionDef(self, node):
        """Visit function definition"""
        self.current_function = node.name
        self.return_value = None
        
        # Process function body
        for stmt in node.body:
            self.visit(stmt)
        
        # If we have a return value, create the main implication
        if self.return_value is not None:
            # For simple functions, the return value represents the function's behavior
            self.assertions.append(self.return_value)
    
    def visit_Return(self, node):
        """Visit return statement"""
        if node.value:
            self.return_value = self.convert_to_z3_expr(node.value)
    
    def visit_If(self, node):
        """Visit if statement and create logical implications"""
        condition = self.convert_to_z3_expr(node.test)
        
        # Process true branch
        true_return = self._extract_return_value(node.body)
        if true_return is not None:
            self.assertions.append(Implies(condition, true_return))
        
        # Process false branch (else/elif)
        false_return = self._extract_return_value(node.orelse)
        if false_return is not None:
            self.assertions.append(Implies(Not(condition), false_return))
        
        # Continue visiting child nodes
        for child in node.body + node.orelse:
            self.visit(child)
    
    def _extract_return_value(self, stmts: List) -> Optional[Any]:
        """Extract return value from a list of statements"""
        for stmt in stmts:
            if isinstance(stmt, ast.Return) and stmt.value:
                return self.convert_to_z3_expr(stmt.value)
            elif isinstance(stmt, ast.If):
                # Handle nested if statements
                condition = self.convert_to_z3_expr(stmt.test)
                true_ret = self._extract_return_value(stmt.body)
                false_ret = self._extract_return_value(stmt.orelse)
                if true_ret is not None and false_ret is not None:
                    return If(condition, true_ret, false_ret)
        return None
    
    def convert_to_z3_expr(self, node) -> Any:
        """Convert Python AST node to Z3 expression"""
        if node is None:
            return None
            
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
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")
    
    def _convert_comparison(self, node: ast.Compare) -> Any:
        """Convert comparison operation"""
        left = self.convert_to_z3_expr(node.left)
        right = self.convert_to_z3_expr(node.comparators[0])
        op = node.ops[0]
        
        if isinstance(op, ast.Eq):
            return left == right
        elif isinstance(op, ast.NotEq):
            return left != right
        elif isinstance(op, ast.Lt):
            return left < right
        elif isinstance(op, ast.LtE):
            return left <= right
        elif isinstance(op, ast.Gt):
            return left > right
        elif isinstance(op, ast.GtE):
            return left >= right
        else:
            raise ValueError(f"Unsupported comparison operator: {type(op)}")
    
    def _convert_bool_op(self, node: ast.BoolOp) -> Any:
        """Convert boolean operation"""
        values = [self.convert_to_z3_expr(v) for v in node.values]
        
        if isinstance(node.op, ast.And):
            return And(*values)
        elif isinstance(node.op, ast.Or):
            return Or(*values)
        else:
            raise ValueError(f"Unsupported boolean operator: {type(node.op)}")
    
    def _convert_unary_op(self, node: ast.UnaryOp) -> Any:
        """Convert unary operation"""
        operand = self.convert_to_z3_expr(node.operand)
        
        if isinstance(node.op, ast.Not):
            return Not(operand)
        else:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
    
    def _convert_bin_op(self, node: ast.BinOp) -> Any:
        """Convert binary operation"""
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
            raise ValueError(f"Unsupported binary operator: {type(node.op)}")
    
    def _convert_name(self, node: ast.Name) -> Any:
        """Convert variable name to Z3 variable"""
        if node.id in self.z3_vars:
            return self.z3_vars[node.id]
        else:
            raise ValueError(f"Undefined variable: {node.id}")
    
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
            raise ValueError(f"Unsupported constant type: {type(value)}")
    
    def _convert_call(self, node: ast.Call) -> Any:
        """Convert function call (limited support)"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == "len" and len(node.args) == 1:
                arg = self.convert_to_z3_expr(node.args[0])
                return Length(arg)
        raise ValueError(f"Unsupported function call: {func_name}")