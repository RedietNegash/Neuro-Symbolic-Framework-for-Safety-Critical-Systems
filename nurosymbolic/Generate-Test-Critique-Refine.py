import ast
from z3 import *

def generate_synthetic_dataset():
    buggy_altitude_code = '''
def check_altitude(altitude):
    if altitude > 40 and altitude < 60:
        return True
    else:
        return False
'''
    correct_altitude_code = '''
def check_altitude(altitude):
    if altitude >= 40 and altitude <= 60:
        return True
    else:
        return False
'''
    buggy_grasp_code = '''
def can_grasp(is_holding, action):
    if action == "Grasp":
        return True
    return not is_holding
'''
    correct_grasp_code = '''
def can_grasp(is_holding, action):
    if action == "Grasp":
        return not is_holding
    return True
'''
    problems = [
        {
            "id": "altitude_40_60",
            "requirement": "The drone must maintain an altitude between 40 and 60 meters inclusive.",
            "buggy_code": buggy_altitude_code,
            "correct_code": correct_altitude_code,
            "formal_property": "And(altitude >= 40, altitude <= 60)"
        },
        {
            "id": "no_grasp_if_holding",
            "requirement": "The robotic arm must never perform a Grasp action if the object is already held.",
            "buggy_code": buggy_grasp_code,
            "correct_code": correct_grasp_code,
            "formal_property": "Implies(action == Grasp, Not(is_holding))"
        }
    ]
    print("[Dataset] Generated", len(problems), "problems")
    return problems

def generate_code_from_llm(prompt, is_refinement=False, dataset=None):
    if dataset is None:
        dataset = generate_synthetic_dataset()
    for item in dataset:
        if item["requirement"].lower() in prompt.lower() or item["id"] in prompt:
            if is_refinement:
                print("[LLM] Refinement for", item["id"])
                return item["correct_code"]
            else:
                print("[LLM] Initial buggy code for", item["id"])
                return item["buggy_code"]
    print("[LLM] Prompt not matched, returning default buggy code")
    return dataset[0]["buggy_code"] if not is_refinement else dataset[0]["correct_code"]

class PythonToZ3Converter(ast.NodeVisitor):
    def __init__(self, z3_vars):
        self.z3_vars = z3_vars
        self.assertions = []

    def visit_FunctionDef(self, node):
        for stmt in node.body:
            self.visit(stmt)

    def visit_If(self, node):
        condition = self.convert_to_z3_expr(node.test)
        true_branch = self.extract_return_value(node.body)
        false_branch = self.extract_return_value(node.orelse)
        if true_branch is not None:
            self.assertions.append(Implies(condition, true_branch))
        if false_branch is not None:
            self.assertions.append(Implies(Not(condition), false_branch))
        for n in node.body + node.orelse:
            self.visit(n)

    def extract_return_value(self, stmts):
        for s in stmts:
            if isinstance(s, ast.Return):
                return self.convert_to_z3_expr(s.value)
        return None

    def convert_to_z3_expr(self, node):
        if node is None:
            return None
        if isinstance(node, ast.Compare):
            left = self.convert_to_z3_expr(node.left)
            right = self.convert_to_z3_expr(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                return left > right
            elif isinstance(op, ast.Lt):
                return left < right
            elif isinstance(op, ast.GtE):
                return left >= right
            elif isinstance(op, ast.LtE):
                return left <= right
            elif isinstance(op, ast.Eq):
                return left == right
            elif isinstance(op, ast.NotEq):
                return left != right
        elif isinstance(node, ast.BoolOp):
            values = [self.convert_to_z3_expr(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return And(values)
            elif isinstance(node.op, ast.Or):
                return Or(values)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return Not(self.convert_to_z3_expr(node.operand))
        elif isinstance(node, ast.Name):
            return self.z3_vars.get(node.id)
        elif isinstance(node, ast.Constant):
            return self.make_const(node.value)
        return None

    def make_const(self, value):
        if isinstance(value, bool):
            return BoolVal(value)
        if isinstance(value, int):
            return IntVal(value)
        if isinstance(value, float):
            return RealVal(value)
        if isinstance(value, str):
            return StringVal(value)
        return value

def verify_code(code_string, formal_property_string, z3_vars):
    print("[Verify] Verifying code...")
    tree = ast.parse(code_string)
    print(tree)
    converter = PythonToZ3Converter(z3_vars)
    converter.visit(tree)
    solver = Solver()
    for a in converter.assertions:
        solver.add(a)
    property_expr = eval(formal_property_string, globals(), z3_vars)
    solver.add(Not(property_expr))
    result = solver.check()
    if result == sat:
        model = solver.model()
        ce = {d.name(): str(model[d]) for d in model.decls()}
        print("[Verify] Failed. Counterexample:", ce)
        return False, ce
    else:
        print("[Verify] Passed. Property holds.")
        return True, None

def run_experiment(problem):
    print("\n--- Experiment:", problem["id"], "---")
    dataset = generate_synthetic_dataset()
    code = generate_code_from_llm(problem["requirement"], False, dataset)
    altitude, = Reals('altitude')
    z3_vars = {
        'altitude': altitude,
        'is_holding': Bool('is_holding'),
        'action': Const('action', StringSort()),
        'Grasp': StringVal('Grasp')
    }
    correct, feedback = verify_code(code, problem["formal_property"], z3_vars)
    if not correct:
        refinement_prompt = f"{problem['requirement']} Counterexample: {feedback}. Fix this."
        refined = generate_code_from_llm(refinement_prompt, True, dataset)
        correct2, feedback2 = verify_code(refined, problem["formal_property"], z3_vars)
        if correct2:
            print("[Refine] Success after refinement.")
        else:
            print("[Refine] Still failing. Counterexample:", feedback2)
    else:
        print("[Experiment] No refinement needed.")

if __name__ == "__main__":
    problems = generate_synthetic_dataset()
    for p in problems:
        run_experiment(p)
