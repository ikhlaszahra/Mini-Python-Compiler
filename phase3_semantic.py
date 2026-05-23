# ════════════════════════════════════════════════════════════
#  PHASE 3 — SEMANTIC ANALYSIS
#  Walks the AST and checks for logical errors:
#    - Variable used before declaration
#    - Variable declared twice in same scope
#    - Function called before definition
#    - Wrong number of arguments to function
# ════════════════════════════════════════════════════════════


class SymbolTable:
    """
    A stack of scopes.
    Each scope is a dict  { name → {'kind': 'var'|'fun', 'params': [...]} }
    """

    def __init__(self):
        self.scopes = [{}]          # start with global scope

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def declare(self, name, info):
        """Add a name to the current (innermost) scope."""
        self.scopes[-1][name] = info

    def lookup(self, name):
        """Search from innermost scope outward."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def is_in_current_scope(self, name):
        return name in self.scopes[-1]


class SemanticAnalyzer:

    def __init__(self):
        self.table  = SymbolTable()
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)

    # ── Pre-register all functions so they can be called
    #    before their definition (like hoisting)
    def pre_register(self, ast):
        for stmt in ast['body']:
            if stmt['kind'] == 'Fun':
                self.table.declare(stmt['name'], {
                    'kind': 'fun',
                    'params': stmt['params']
                })

    # ── Walk the full AST ────────────────────────────────────

    def analyze(self, ast):
        self.pre_register(ast)
        for stmt in ast['body']:
            self.check_stmt(stmt)
        return self.errors

    def check_stmts(self, stmts):
        for s in stmts:
            self.check_stmt(s)

    def check_stmt(self, stmt):
        kind = stmt['kind']

        if kind == 'Let':
            if self.table.is_in_current_scope(stmt['name']):
                self.error(
                    f"[Semantic Error] Line {stmt['line']}: "
                    f"Variable '{stmt['name']}' already declared in this scope."
                )
            self.check_expr(stmt['value'])
            self.table.declare(stmt['name'], {'kind': 'var'})

        elif kind == 'Assign':
            if self.table.lookup(stmt['name']) is None:
                self.error(
                    f"[Semantic Error] Line {stmt.get('line','?')}: "
                    f"Variable '{stmt['name']}' used before declaration."
                )
            self.check_expr(stmt['value'])

        elif kind == 'If':
            self.check_expr(stmt['cond'])
            self.table.enter_scope()
            self.check_stmts(stmt['then'])
            self.table.exit_scope()
            if stmt['else_']:
                self.table.enter_scope()
                self.check_stmts(stmt['else_'])
                self.table.exit_scope()

        elif kind == 'While':
            self.check_expr(stmt['cond'])
            self.table.enter_scope()
            self.check_stmts(stmt['body'])
            self.table.exit_scope()

        elif kind == 'Fun':
            # Register params as variables inside the function scope
            self.table.enter_scope()
            for p in stmt['params']:
                self.table.declare(p, {'kind': 'var'})
            self.check_stmts(stmt['body'])
            self.table.exit_scope()

        elif kind == 'Return':
            self.check_expr(stmt['value'])

        elif kind == 'Print':
            self.check_expr(stmt['value'])

        elif kind == 'ExprStmt':
            self.check_expr(stmt['expr'])

    def check_expr(self, expr):
        kind = expr['kind']

        if kind == 'Var':
            if self.table.lookup(expr['name']) is None:
                self.error(
                    f"[Semantic Error] Line {expr['line']}: "
                    f"Variable '{expr['name']}' used before declaration."
                )

        elif kind == 'BinOp':
            self.check_expr(expr['left'])
            self.check_expr(expr['right'])

        elif kind == 'Unary':
            self.check_expr(expr['expr'])

        elif kind == 'Call':
            info = self.table.lookup(expr['name'])
            if info is None:
                self.error(
                    f"[Semantic Error] Line {expr['line']}: "
                    f"Function '{expr['name']}' not defined."
                )
            elif info['kind'] == 'fun':
                expected = len(info['params'])
                got      = len(expr['args'])
                if expected != got:
                    self.error(
                        f"[Semantic Error] Line {expr['line']}: "
                        f"'{expr['name']}' expects {expected} argument(s), got {got}."
                    )
            for arg in expr['args']:
                self.check_expr(arg)

        # Num / Str — nothing to check
