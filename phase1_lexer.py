# ════════════════════════════════════════════════════════════
#  PHASE 1 — LEXICAL ANALYSIS
#  Reads source code character by character and produces tokens
# ════════════════════════════════════════════════════════════

# Every word / symbol in the language belongs to one of these types
TOKEN_TYPES = {
    # Keywords
    'let', 'if', 'else', 'while', 'fun', 'return', 'print',
    # Literals & names
    'NUMBER', 'STRING', 'ID',
    # Operators
    'PLUS', 'MINUS', 'MUL', 'DIV', 'MOD',
    'EQ', 'NEQ', 'LT', 'GT', 'LE', 'GE', 'ASSIGN',
    # Symbols
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'COMMA', 'SEMICOLON',
    # Special
    'EOF'
}

KEYWORDS = {'let', 'if', 'else', 'while', 'fun', 'return', 'print'}

# A Token is just a small container: type + value + line number
class Token:
    def __init__(self, type_, value, line):
        self.type  = type_
        self.value = value
        self.line  = line

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'


class Lexer:
    """
    Turns raw source text into a flat list of Token objects.
    No external libraries — pure Python.
    """

    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.tokens = []
        self.errors = []

    # ── Helpers ──────────────────────────────────────────────

    def current(self):
        return self.source[self.pos] if self.pos < len(self.source) else '\0'

    def peek_next(self):
        p = self.pos + 1
        return self.source[p] if p < len(self.source) else '\0'

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def add(self, type_, value):
        self.tokens.append(Token(type_, value, self.line))

    # ── Main tokenizer ───────────────────────────────────────

    def tokenize(self):
        while self.pos < len(self.source):
            ch = self.current()

            # Skip whitespace
            if ch in ' \t\r\n':
                self.advance()

            # Skip single-line comments  (# this is a comment)
            elif ch == '#':
                while self.pos < len(self.source) and self.current() != '\n':
                    self.advance()

            # Number literal  e.g. 42  or  3.14
            elif ch.isdigit():
                self._read_number()

            # String literal  e.g. "hello"
            elif ch == '"':
                self._read_string()

            # Identifier or keyword  e.g. let  x  while  myVar
            elif ch.isalpha() or ch == '_':
                self._read_word()

            # Two-character operators
            elif ch == '=' and self.peek_next() == '=':
                self.advance(); self.advance(); self.add('EQ', '==')
            elif ch == '!' and self.peek_next() == '=':
                self.advance(); self.advance(); self.add('NEQ', '!=')
            elif ch == '<' and self.peek_next() == '=':
                self.advance(); self.advance(); self.add('LE', '<=')
            elif ch == '>' and self.peek_next() == '=':
                self.advance(); self.advance(); self.add('GE', '>=')

            # Single-character tokens
            elif ch == '=': self.advance(); self.add('ASSIGN', '=')
            elif ch == '<': self.advance(); self.add('LT', '<')
            elif ch == '>': self.advance(); self.add('GT', '>')
            elif ch == '+': self.advance(); self.add('PLUS', '+')
            elif ch == '-': self.advance(); self.add('MINUS', '-')
            elif ch == '*': self.advance(); self.add('MUL', '*')
            elif ch == '/': self.advance(); self.add('DIV', '/')
            elif ch == '%': self.advance(); self.add('MOD', '%')
            elif ch == '(': self.advance(); self.add('LPAREN', '(')
            elif ch == ')': self.advance(); self.add('RPAREN', ')')
            elif ch == '{': self.advance(); self.add('LBRACE', '{')
            elif ch == '}': self.advance(); self.add('RBRACE', '}')
            elif ch == ',': self.advance(); self.add('COMMA', ',')
            elif ch == ';': self.advance(); self.add('SEMICOLON', ';')

            else:
                self.errors.append(f'[Lexer Error] Line {self.line}: Unknown character {ch!r}')
                self.advance()

        self.add('EOF', 'EOF')
        return self.tokens

    def _read_number(self):
        start = self.pos
        while self.current().isdigit():
            self.advance()
        if self.current() == '.' and self.peek_next().isdigit():
            self.advance()
            while self.current().isdigit():
                self.advance()
        raw = self.source[start:self.pos]
        value = float(raw) if '.' in raw else int(raw)
        self.add('NUMBER', value)

    def _read_string(self):
        self.advance()          # skip opening "
        start = self.pos
        while self.pos < len(self.source) and self.current() != '"':
            self.advance()
        value = self.source[start:self.pos]
        if self.current() == '"':
            self.advance()      # skip closing "
        else:
            self.errors.append(f'[Lexer Error] Line {self.line}: Unterminated string')
        self.add('STRING', value)

    def _read_word(self):
        start = self.pos
        while self.current().isalnum() or self.current() == '_':
            self.advance()
        word = self.source[start:self.pos]
        # Is it a keyword or an identifier?
        self.add(word if word in KEYWORDS else 'ID', word)
