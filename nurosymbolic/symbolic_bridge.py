# symbolic_bridge.py
import ast
import z3
from typing import Dict, Any, List

class ASTToZ3Translator:
    """
    Fixed Symbolic Bridge Component
    """
    
    def __init__(self):
        self.variables = {}
        self.current_function = None
        
    def python_code_to_z3(self, code_snippet: str, function_name: str = None) -> z3.BoolRef:
        """Parse Python code and convert to Z3 expressions - handle document patterns"""
        try:
            clean_code = self._clean_document_code(code_snippet)
            
            if not clean_code.startswith('def '):
                clean_code = f"def temp_function():\n    return {clean_code}"
            
            tree = ast.parse(clean_code)
            self.current_function = function_name
            self.variables = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return self.visit_FunctionDef(node)
            
            return z3.BoolVal(True)
            
        except Exception as e:
            print(f"Translation error: {e}")
            return z3.BoolVal(False)
    
    def visit(self, node):
        """Dispatch method for visiting AST nodes"""
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def visit_FunctionDef(self, node):
        """Visit function definition"""
        conditions = []
        return_found = False
        
        for stmt in node.body:
            result = self.visit(stmt)
            if result is not None:
                if isinstance(result, tuple) and result[0] == 'return':
                    return_found = True
                    conditions.append(result[1])
                else:
                    conditions.append(result)
        
        if conditions:
            if return_found:
                return conditions[-1] 
            return z3.And(conditions)
        return z3.BoolVal(True)
    
    def visit_Return(self, node):
        """Visit return statement"""
        return ('return', self.visit(node.value))
    
    def visit_If(self, node):
        """Visit if statement - convert to implication"""
        test_condition = self.visit(node.test)
        

        then_conditions = []
        for stmt in node.body:
            result = self.visit(stmt)
            if result is not None:
                if isinstance(result, tuple) and result[0] == 'return':
                    then_conditions.append(result[1])
                else:
                    then_conditions.append(result)
        
        then_expr = z3.And(then_conditions) if then_conditions else z3.BoolVal(True)
        

        else_conditions = []
        for stmt in node.orelse:
            result = self.visit(stmt)
            if result is not None:
                if isinstance(result, tuple) and result[0] == 'return':
                    else_conditions.append(result[1])
                else:
                    else_conditions.append(result)
        
        else_expr = z3.And(else_conditions) if else_conditions else z3.BoolVal(True)
        
        return z3.And(
            z3.Implies(test_condition, then_expr),
            z3.Implies(z3.Not(test_condition), else_expr)
        )


    def visit_Compare(self, node):
        """Visit comparison operations with simplified string handling"""
        left = self.visit(node.left)
        
        if len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            right = self.visit(node.comparators[0])
            

            if (hasattr(left, 'sort') and left.sort() == z3.StringSort()) or \
            (hasattr(right, 'sort') and right.sort() == z3.StringSort()):
                
                if isinstance(op, ast.Eq):
                    comp_var = z3.Bool(f"str_eq_{str(left)}_{str(right)}")
                    return comp_var
                elif isinstance(op, ast.NotEq):
                    comp_var = z3.Bool(f"str_neq_{str(left)}_{str(right)}")
                    return z3.Not(comp_var)
                else:
                    return z3.BoolVal(True)
            else:
                return self.visit_compare_op(op, left, right)
        else:
            result = None
            prev = left
            for op, comparator in zip(node.ops, node.comparators):
                current = self.visit_compare_op(op, prev, self.visit(comparator))
                if result is None:
                    result = current
                else:
                    result = z3.And(result, current)
                prev = self.visit(comparator)
            return result
    
    def visit_compare_op(self, op, left, right):
        """Handle comparison operators with type checking"""
        if z3.is_int(left) and z3.is_real(right):
            left = z3.ToReal(left)
        elif z3.is_real(left) and z3.is_int(right):
            right = z3.ToReal(right)
        
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
            return left == right
    
    def visit_BoolOp(self, node):
        """Visit boolean operations (and, or)"""
        values = [self.visit(value) for value in node.values]
        
        if isinstance(node.op, ast.And):
            return z3.And(values)
        elif isinstance(node.op, ast.Or):
            return z3.Or(values)
        else:
            return z3.And(values)
    
    def visit_BinOp(self, node):
        """Visit binary operations"""
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right
        else:
            return left
    

    def visit_Name(self, node):
        """Visit variable names - use boolean variables for actions"""
        var_name = node.id
        if var_name not in self.variables:
            if var_name == "action":
                self.variables[var_name] = z3.Bool(f"action_is_Grasp")
            elif "is_holding" in var_name:
                self.variables[var_name] = z3.Bool(var_name)
            elif any(pattern in var_name for pattern in ["altitude", "speed", "distance", "voltage"]):
                self.variables[var_name] = z3.Real(var_name)
            else:
                self.variables[var_name] = z3.Real(var_name)
        return self.variables[var_name]
    
    def visit_Constant(self, node):
        """Visit constants with proper type handling"""
        if isinstance(node.value, bool):
            return z3.BoolVal(node.value)
        elif isinstance(node.value, int):
            return z3.IntVal(node.value)
        elif isinstance(node.value, float):
            return z3.RealVal(node.value)
        elif isinstance(node.value, str):
            return z3.StringVal(node.value)
        else:
            return z3.IntVal(0)
    
    def visit_Assign(self, node):
        """Visit assignment statements with proper type inference"""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            value = self.visit(node.value)
            
            print(f"DEBUG Assignment: {var_name} = {ast.dump(node.value)}")
            print(f"DEBUG Value type: {type(value)}")
            
            if var_name not in self.variables:
                if self._expression_produces_boolean(node.value):
                    self.variables[var_name] = z3.Bool(var_name)
                    print(f"DEBUG: Created {var_name} as Boolean")
                else:
                    self.variables[var_name] = z3.Real(var_name)
                    print(f"DEBUG: Created {var_name} as Real")
            
            return self.variables[var_name] == value
        
        return z3.BoolVal(True)

    def _expression_produces_boolean(self, ast_node):
        """Check if an AST node produces a Boolean result"""
        if isinstance(ast_node, ast.Compare):
            return True
        if isinstance(ast_node, ast.BoolOp):
            return True
        if isinstance(ast_node, ast.UnaryOp):
            return True
        if isinstance(ast_node, ast.Call):
            return True
        if isinstance(ast_node, ast.Name) and ast_node.id in self.variables:
            return z3.is_bool(self.variables[ast_node.id])
        
        return False
    
    def visit_Call(self, node):
        """Visit function calls - limited support"""
        return z3.BoolVal(True)
    
    def generic_visit(self, node):
        """Generic visitor for unsupported nodes"""
        return z3.BoolVal(True)
    
    def _clean_document_code(self, code: str) -> str:
        """Clean code while preserving document-style patterns"""
        lines = code.split('\n')
        clean_lines = []
        
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('return '):
                clean_lines.append(line)
            elif line.strip().startswith('if ') or line.strip().startswith('else:'):
                clean_lines.append(line)
        
        return '\n'.join(clean_lines) if clean_lines else code

    
    