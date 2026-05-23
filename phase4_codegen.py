# ════════════════════════════════════════════════════════════
#  PHASE 4 — INTERMEDIATE CODE GENERATION
#  Converts the AST into Three-Address Code (TAC)
#
#  TAC rules:
#    - At most ONE operation per line
#    - Uses temporary variables  t1, t2, t3 …
#    - Uses labels               L1, L2, L3 …
#
#  Example:
#    source :  let c = a + b * 2;
#    TAC    :  t1 = b * 2
#              t2 = a + t1
#              c  = t2
# ════════════════════════════════════════════════════════════


class CodeGenerator:

    def __init__(self):
        self.code       = []    # list of TAC instruction strings
        self.temp_count = 0
        self.label_count = 0

    # ── Helpers ──────────────────────────────────────────────

    def new_temp(self):
        self.temp_count += 1
        return f't{self.temp_count}'

    def new_label(self):
        self.label_count += 1
        return f'L{self.label_count}'

    def emit(self, line):
        self.code.append(line)

    # ── Entry point ──────────────────────────────────────────

    def generate(self, ast):
        for stmt in ast['body']:
            self.gen_stmt(stmt)
        return self.code

    # ── Statements ────────────────────────────────────────────

    def gen_stmt(self, stmt):
        kind = stmt['kind']

        if kind == 'Let':
            val = self.gen_expr(stmt['value'])
            self.emit(f"{stmt['name']} = {val}")

        elif kind == 'Assign':
            val = self.gen_expr(stmt['value'])
            self.emit(f"{stmt['name']} = {val}")

        elif kind == 'Print':
            val = self.gen_expr(stmt['value'])
            self.emit(f'PRINT {val}')

        elif kind == 'Return':
            val = self.gen_expr(stmt['value'])
            self.emit(f'RETURN {val}')

        elif kind == 'ExprStmt':
            self.gen_expr(stmt['expr'])

        elif kind == 'If':
            self._gen_if(stmt)

        elif kind == 'While':
            self._gen_while(stmt)

        elif kind == 'Fun':
            self._gen_fun(stmt)

    def _gen_if(self, stmt):
        cond      = self.gen_expr(stmt['cond'])
        else_lbl  = self.new_label()
        end_lbl   = self.new_label()

        self.emit(f'IF_FALSE {cond} GOTO {else_lbl}')

        for s in stmt['then']:
            self.gen_stmt(s)

        self.emit(f'GOTO {end_lbl}')
        self.emit(f'{else_lbl}:')

        if stmt['else_']:
            for s in stmt['else_']:
                self.gen_stmt(s)

        self.emit(f'{end_lbl}:')

    def _gen_while(self, stmt):
        start_lbl = self.new_label()
        end_lbl   = self.new_label()

        self.emit(f'{start_lbl}:')
        cond = self.gen_expr(stmt['cond'])
        self.emit(f'IF_FALSE {cond} GOTO {end_lbl}')

        for s in stmt['body']:
            self.gen_stmt(s)

        self.emit(f'GOTO {start_lbl}')
        self.emit(f'{end_lbl}:')

    def _gen_fun(self, stmt):
        params_str = ', '.join(stmt['params'])
        self.emit(f"FUNC_BEGIN {stmt['name']}({params_str})")

        for s in stmt['body']:
            self.gen_stmt(s)

        self.emit(f"FUNC_END {stmt['name']}")

    # ── Expressions ───────────────────────────────────────────

    def gen_expr(self, expr):
        kind = expr['kind']

        if kind == 'Num':
            return str(expr['value'])

        if kind == 'Str':
            return f'"{expr["value"]}"'

        if kind == 'Var':
            return expr['name']

        if kind == 'Unary':
            operand = self.gen_expr(expr['expr'])
            tmp     = self.new_temp()
            self.emit(f'{tmp} = -{operand}')
            return tmp

        if kind == 'BinOp':
            left  = self.gen_expr(expr['left'])
            right = self.gen_expr(expr['right'])
            tmp   = self.new_temp()
            self.emit(f'{tmp} = {left} {expr["op"]} {right}')
            return tmp

        if kind == 'Call':
            arg_temps = [self.gen_expr(a) for a in expr['args']]
            for t in arg_temps:
                self.emit(f'PARAM {t}')
            tmp = self.new_temp()
            self.emit(f'{tmp} = CALL {expr["name"]}, {len(arg_temps)}')
            return tmp

        return '0'
