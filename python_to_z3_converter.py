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
            # Ensure it's a boolean for Z3
            self.assertions.append(self._ensure_bool(self.return_value))
    
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
    
    def visit_For(self, node):
        """Handle bounded loop unrolling (simple case)"""
        # We assume the loop is over a range or a fixed list
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == "range" and len(node.iter.args) <= 2:
                # Basic range(N) or range(start, stop)
                try:
                    args = [int(arg.value) if isinstance(arg, ast.Constant) else None for arg in node.iter.args]
                    if None not in args:
                        start = args[0] if len(args) == 2 else 0
                        stop = args[1] if len(args) == 2 else args[0]
                        # Unroll the loop body N times
                        for i in range(start, stop):
                            # We'd need to handle loop variable here, but for simple safety logic, 
                            # we'll just visit the body. Real unrolling would require symbolic state tracking.
                            for stmt in node.body:
                                self.visit(stmt)
                except Exception as e:
                    print(f"Loop unrolling failed: {e}")

    def get_negated_property(self, property_expr) -> Any:
        """Explicitly generate ¬ϕ"""
        return Not(property_expr)

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
        elif isinstance(node, ast.Attribute):
            return self._convert_attribute(node)
        elif isinstance(node, ast.Subscript):
            return self._convert_subscript(node)
        elif isinstance(node, ast.IfExp):
            raise ValueError(f"Unsupported AST node: {type(node)} - Do not use ternary operators (x if condition else y). Use simple boolean expressions.")
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")
    
    def _convert_comparison(self, node: ast.Compare) -> Any:
        """Convert comparison operation (handles chained comparisonsLike 40 <= x <= 60)"""
        comparisons = []
        left = self.convert_to_z3_expr(node.left)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self.convert_to_z3_expr(comparator)
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
                raise ValueError(f"Unsupported comparison operator: {type(op)}")
            left = right # For chained comparisons: next comparison starts from current right
            
        if len(comparisons) == 1:
            return comparisons[0]
        return And(*comparisons)

    def _ensure_bool(self, expr: Any) -> Any:
        """Ensure a Z3 expression is a boolean for use in logical contexts"""
        if is_bool(expr):
            return expr
        # Handle truthiness for numbers
        if is_int(expr) or is_real(expr):
            return expr != 0
        # Handle truthiness for strings
        if is_string(expr):
            return Length(expr) > 0
        return expr
    
    def _convert_bool_op(self, node: ast.BoolOp) -> Any:
        """Convert boolean operation"""
        values = [self._ensure_bool(self.convert_to_z3_expr(v)) for v in node.values]
        
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
            return Not(self._ensure_bool(operand))
        elif isinstance(node.op, ast.Invert):
            raise ValueError(f"Unsupported unary operator: {type(node.op)} - Use 'not' instead of '~' for logical negation")
        elif isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.UAdd):
            return operand
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
        elif isinstance(node.op, ast.BitAnd):
            # Convert bitwise AND to logical AND for boolean context
            return And(left != 0, right != 0)
        elif isinstance(node.op, ast.BitXor):
            # Convert bitwise XOR - not recommended but handle it
            raise ValueError(f"Unsupported binary operator: {type(node.op)} - Use 'and'/'or' instead of '^'")
        elif isinstance(node.op, ast.BitOr):
            # Convert bitwise OR
            raise ValueError(f"Unsupported binary operator: {type(node.op)} - Use 'and'/'or' instead of '|'")
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
    
    def _convert_attribute(self, node: ast.Attribute) -> Any:
        """Handle attribute access (e.g., drone.altitude) by mapping to flat variable if found"""
        if node.attr in self.z3_vars:
            return self.z3_vars[node.attr]
        raise ValueError(f"Undefined attribute: {node.attr}")

    def _convert_subscript(self, node: ast.Subscript) -> Any:
        """Handle subscript access (e.g., drone['altitude']) by mapping to flat variable if found"""
        # Handle different Python AST structures for slices
        target_name = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            target_name = node.slice.value
        elif isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Constant) and isinstance(node.slice.value.value, str):
            target_name = node.slice.value.value
        elif isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Str):
            target_name = node.slice.value.s # Older python
        elif isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            # Trying to access array index
            raise ValueError(f"Unsupported subscript access: Array indexing not supported. Use direct variable names as function parameters.")
            
        if target_name and target_name in self.z3_vars:
            return self.z3_vars[target_name]
            
        raise ValueError(f"Unsupported subscript access: {ast.dump(node)}. Use direct variable names as function parameters, not dictionary or array access.")
        
    def _convert_call(self, node: ast.Call) -> Any:
        """Convert function call (limited support)"""
        f_name = "complex"
        if isinstance(node.func, ast.Name):
            f_name = node.func.id
            if f_name == "len" and len(node.args) == 1:
                arg = self.convert_to_z3_expr(node.args[0])
                return Length(arg)
            elif f_name == "isinstance" and len(node.args) == 2:
                return BoolVal(True)
            elif f_name == "print":
                return None
            elif f_name in ["abs", "Abs"] and len(node.args) == 1:
                arg = self.convert_to_z3_expr(node.args[0])
                return If(arg >= 0, arg, -arg) # Z3 Abs implementation
            elif f_name in ["int", "float", "str", "bool"]:
                raise ValueError(f"Unsupported function call: {f_name} - Do not use type conversion functions")
        raise ValueError(f"Unsupported function call: {f_name}")