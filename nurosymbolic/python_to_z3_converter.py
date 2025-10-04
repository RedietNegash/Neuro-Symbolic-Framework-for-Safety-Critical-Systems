# python_to_z3_converter.py
import ast
from typing import Dict, List, Optional, Any
from z3 import *

class PythonToZ3Converter(ast.NodeVisitor):
    def __init__(self, z3_vars: Dict):
        self.z3_vars = z3_vars
        self.assertions = []
        self.current_function = None
        self.function_return = None
    
    def visit_FunctionDef(self, node):
        print(f"DEBUG_CONVERTER: Processing function {node.name}")
        self.current_function = node.name
        self.function_return = None
        self.function_return = Bool('function_return')
        

        for stmt in node.body:
            self.visit(stmt)
        
        print(f"DEBUG_CONVERTER: Function {node.name} logic complete")
    
    def visit_Return(self, node):
        print(f"DEBUG_CONVERTER: Found return statement")
        if node.value:
            return_expr = self.convert_to_z3_expr(node.value)
            print(f"DEBUG_CONVERTER: Return expression: {return_expr}")
            
            pass
    
    def visit_If(self, node):
        print(f"DEBUG_CONVERTER: Processing if statement")
        condition = self.convert_to_z3_expr(node.test)
        print(f"DEBUG_CONVERTER: If condition: {condition}")
        

        true_return = self._extract_return_value(node.body)
        if true_return is not None:
            self.assertions.append(Implies(condition, self.function_return == true_return))
            print(f"DEBUG_CONVERTER: True branch: if {condition} then return {true_return}")
        
      
        false_return = self._extract_return_value(node.orelse)
        if false_return is not None:
            self.assertions.append(Implies(Not(condition), self.function_return == false_return))
            print(f"DEBUG_CONVERTER: False branch: if not {condition} then return {false_return}")
        elif node.orelse:
            pass
        
        for child in node.body + node.orelse:
            self.visit(child)
    
    def _extract_return_value(self, stmts: List) -> Optional[Any]:
        """Extract what would be returned from a block of statements"""
        for stmt in stmts:
            if isinstance(stmt, ast.Return) and stmt.value:
                return_val = self.convert_to_z3_expr(stmt.value)
                print(f"DEBUG_CONVERTER: Extracted return value: {return_val}")
                return return_val
            elif isinstance(stmt, ast.If):
                condition = self.convert_to_z3_expr(stmt.test)
                true_ret = self._extract_return_value(stmt.body)
                false_ret = self._extract_return_value(stmt.orelse)
                if true_ret is not None and false_ret is not None:
                    if_expr = If(condition, true_ret, false_ret)
                    print(f"DEBUG_CONVERTER: Created if expression: {if_expr}")
                    return if_expr
        return None

    def convert_to_z3_expr(self, node) -> Any:
        if node is None:
            return None
            
        if isinstance(node, ast.Compare):
            result = self._convert_comparison(node)
            print(f"DEBUG_CONVERTER: Converted comparison: {node} -> {result}")
            return result
        elif isinstance(node, ast.BoolOp):
            result = self._convert_bool_op(node)
            print(f"DEBUG_CONVERTER: Converted bool op: {node} -> {result}")
            return result
        elif isinstance(node, ast.UnaryOp):
            result = self._convert_unary_op(node)
            print(f"DEBUG_CONVERTER: Converted unary op: {node} -> {result}")
            return result
        elif isinstance(node, ast.BinOp):
            result = self._convert_bin_op(node)
            print(f"DEBUG_CONVERTER: Converted bin op: {node} -> {result}")
            return result
        elif isinstance(node, ast.Name):
            result = self._convert_name(node)
            print(f"DEBUG_CONVERTER: Converted name: {node.id} -> {result}")
            return result
        elif isinstance(node, ast.Constant):
            result = self._convert_constant(node)
            print(f"DEBUG_CONVERTER: Converted constant: {node.value} -> {result}")
            return result
        elif isinstance(node, ast.Call):
            result = self._convert_call(node)
            print(f"DEBUG_CONVERTER: Converted call: {node} -> {result}")
            return result
        else:
            print(f"DEBUG_CONVERTER: Unsupported node type: {type(node)}")
            raise ValueError(f"Unsupported AST node: {type(node)}")
    
    def _convert_comparison(self, node: ast.Compare) -> Any:
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
        values = [self.convert_to_z3_expr(v) for v in node.values]
        
        if isinstance(node.op, ast.And):
            return And(*values)
        elif isinstance(node.op, ast.Or):
            return Or(*values)
        else:
            raise ValueError(f"Unsupported boolean operator: {type(node.op)}")
    
    def _convert_unary_op(self, node: ast.UnaryOp) -> Any:
        operand = self.convert_to_z3_expr(node.operand)
        
        if isinstance(node.op, ast.Not):
            return Not(operand)
        else:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
    
    def _convert_bin_op(self, node: ast.BinOp) -> Any:
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
        if node.id in self.z3_vars:
            return self.z3_vars[node.id]
        else:
            raise ValueError(f"Undefined variable: {node.id}")
    
    def _convert_constant(self, node: ast.Constant) -> Any:
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
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == "len" and len(node.args) == 1:
                arg = self.convert_to_z3_expr(node.args[0])
                return Length(arg)
        raise ValueError(f"Unsupported function call: {func_name}")