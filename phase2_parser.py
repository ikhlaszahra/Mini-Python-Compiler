# ════════════════════════════════════════════════════════════
#  PHASE 2 — SYNTAX ANALYSIS  (Parser → AST)
#  Reads tokens and builds an Abstract Syntax Tree (AST)
#
#  Grammar (simplified):
#    program     → statement*
#    statement   → let_stmt | if_stmt | while_stmt
#                | fun_stmt | return_stmt | print_stmt
#                | assign_stmt | expr_stmt
#    expression  → comparison ( (and|or) comparison )*
#    comparison  → add ( (==|!=|<|>|<=|>=) add )*
#    add         → mul ( (+|-) mul )*
#    mul         → unary ( (*|/|%) unary )*
#    unary       → - unary | primary
#    primary     → NUMBER | STRING | ID | ID(...) | (expr)
# ════════════════════════════════════════════════════════════

class ParseError(Exception):
    pass


# ── AST Node helpers ─────────────────────────────────────────
# Each node is just a plain dict so it's easy to read/print.

def node(kind, **kwargs):
    return {'kind': kind, **kwargs}


class Parser:

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0
        self.errors = []

    # ── Token navigation ─────────────────────────────────────

    def peek(self):
        return self.tokens[self.pos]

    def peek_type(self):
        return self.tokens[self.pos].type

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != 'EOF':
            self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.peek()
        if tok.type != type_:
            msg = f'[Syntax Error] Line {tok.line}: Expected {type_!r} but got {tok.type!r} ({tok.value!r})'
            self.errors.append(msg)
            raise ParseError(msg)
        return self.advance()

    def match(self, *types):
        if self.peek_type() in types:
            return self.advance()
        return None

    # ── Top level ─────────────────────────────────────────────

    def parse(self):
        stmts = []
        while self.peek_type() != 'EOF':
            try:
                stmts.append(self.parse_statement())
            except ParseError:
                # Error recovery: skip to next semicolon or brace
                while self.peek_type() not in ('SEMICOLON', 'RBRACE', 'EOF'):
                    self.advance()
                self.match('SEMICOLON')
        return node('Program', body=stmts)

    # ── Statements ────────────────────────────────────────────

    def parse_statement(self):
        t = self.peek_type()

        if t == 'let':
            return self.parse_let()
        if t == 'if':
            return self.parse_if()
        if t == 'while':
            return self.parse_while()
        if t == 'fun':
            return self.parse_fun()
        if t == 'return':
            return self.parse_return()
        if t == 'print':
            return self.parse_print()

        # assignment  or  expression statement
        return self.parse_assign_or_expr()

    def parse_let(self):
        line = self.peek().line
        self.expect('let')
        name = self.expect('ID').value
        self.expect('ASSIGN')
        value = self.parse_expr()
        self.expect('SEMICOLON')
        return node('Let', name=name, value=value, line=line)

    def parse_assign_or_expr(self):
        # Peek ahead: if next-next is ASSIGN it's an assignment
        expr = self.parse_expr()
        if self.peek_type() == 'ASSIGN' and expr['kind'] == 'Var':
            self.advance()           # consume =
            rhs = self.parse_expr()
            self.expect('SEMICOLON')
            return node('Assign', name=expr['name'], value=rhs, line=expr['line'])
        self.expect('SEMICOLON')
        return node('ExprStmt', expr=expr)

    def parse_if(self):
        line = self.peek().line
        self.expect('if')
        self.expect('LPAREN')
        cond = self.parse_expr()
        self.expect('RPAREN')
        then_block = self.parse_block()
        else_block = None
        if self.match('else'):
            else_block = self.parse_block()
        return node('If', cond=cond, then=then_block, else_=else_block, line=line)

    def parse_while(self):
        line = self.peek().line
        self.expect('while')
        self.expect('LPAREN')
        cond = self.parse_expr()
        self.expect('RPAREN')
        body = self.parse_block()
        return node('While', cond=cond, body=body, line=line)

    def parse_fun(self):
        line = self.peek().line
        self.expect('fun')
        name = self.expect('ID').value
        self.expect('LPAREN')
        params = []
        if self.peek_type() != 'RPAREN':
            params.append(self.expect('ID').value)
            while self.match('COMMA'):
                params.append(self.expect('ID').value)
        self.expect('RPAREN')
        body = self.parse_block()
        return node('Fun', name=name, params=params, body=body, line=line)

    def parse_return(self):
        line = self.peek().line
        self.expect('return')
        value = self.parse_expr()
        self.expect('SEMICOLON')
        return node('Return', value=value, line=line)

    def parse_print(self):
        line = self.peek().line
        self.expect('print')
        self.expect('LPAREN')
        value = self.parse_expr()
        self.expect('RPAREN')
        self.expect('SEMICOLON')
        return node('Print', value=value, line=line)

    def parse_block(self):
        self.expect('LBRACE')
        stmts = []
        while self.peek_type() not in ('RBRACE', 'EOF'):
            try:
                stmts.append(self.parse_statement())
            except ParseError:
                while self.peek_type() not in ('SEMICOLON', 'RBRACE', 'EOF'):
                    self.advance()
                self.match('SEMICOLON')
        self.expect('RBRACE')
        return stmts

    # ── Expressions (precedence climbing) ────────────────────

    def parse_expr(self):
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_add()
        while self.peek_type() in ('EQ', 'NEQ', 'LT', 'GT', 'LE', 'GE'):
            op   = self.advance().value
            right = self.parse_add()
            left = node('BinOp', op=op, left=left, right=right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.peek_type() in ('PLUS', 'MINUS'):
            op    = self.advance().value
            right = self.parse_mul()
            left  = node('BinOp', op=op, left=left, right=right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.peek_type() in ('MUL', 'DIV', 'MOD'):
            op    = self.advance().value
            right = self.parse_unary()
            left  = node('BinOp', op=op, left=left, right=right)
        return left

    def parse_unary(self):
        if self.peek_type() == 'MINUS':
            line = self.peek().line
            self.advance()
            expr = self.parse_unary()
            return node('Unary', op='-', expr=expr, line=line)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()

        if tok.type == 'NUMBER':
            self.advance()
            return node('Num', value=tok.value, line=tok.line)

        if tok.type == 'STRING':
            self.advance()
            return node('Str', value=tok.value, line=tok.line)

        if tok.type == 'ID':
            self.advance()
            # Function call?
            if self.peek_type() == 'LPAREN':
                self.advance()
                args = []
                if self.peek_type() != 'RPAREN':
                    args.append(self.parse_expr())
                    while self.match('COMMA'):
                        args.append(self.parse_expr())
                self.expect('RPAREN')
                return node('Call', name=tok.value, args=args, line=tok.line)
            return node('Var', name=tok.value, line=tok.line)

        if tok.type == 'LPAREN':
            self.advance()
            expr = self.parse_expr()
            self.expect('RPAREN')
            return expr

        msg = f'[Syntax Error] Line {tok.line}: Unexpected token {tok.type!r} ({tok.value!r})'
        self.errors.append(msg)
        raise ParseError(msg)
