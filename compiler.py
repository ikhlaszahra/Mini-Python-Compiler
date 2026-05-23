# ════════════════════════════════════════════════════════════
#  MAIN COMPILER DRIVER  (compiler.py)
#  Run:  python compiler.py
#  Or :  python compiler.py --demo factorial
#  Or :  python compiler.py --file mycode.txt
# ════════════════════════════════════════════════════════════

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from phase1_lexer    import Lexer
from phase2_parser   import Parser
from phase3_semantic import SemanticAnalyzer
from phase4_codegen  import CodeGenerator
from phase5_optimizer import Optimizer
from phase6_vm       import VirtualMachine

# ── Terminal colours (work on any OS with a modern terminal) ─
RESET  = '\033[0m'
BOLD   = '\033[1m'
CYAN   = '\033[96m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
BLUE   = '\033[94m'
MAGENTA= '\033[95m'
WHITE  = '\033[97m'
DIM    = '\033[2m'

def col(text, color):   return f'{color}{text}{RESET}'
def bold(text):         return f'{BOLD}{text}{RESET}'

# ── Pretty print helpers ─────────────────────────────────────

LINE  = '─' * 60
DLINE = '═' * 60

def header(title):
    print(f'\n{col(DLINE, CYAN)}')
    print(col(f'  {title}', BOLD + CYAN))
    print(col(DLINE, CYAN))

def sub(title, color=YELLOW):
    print(f'\n  {col("▶", color)} {bold(title)}')
    print(f'  {col(LINE, DIM)}')

def ok(msg):   print(col(f'  ✔  {msg}', GREEN))
def err(msg):  print(col(f'  ✖  {msg}', RED))
def info_line(msg): print(f'  {col("•", BLUE)} {msg}')

# ── Token colour coding ──────────────────────────────────────

TOKEN_COLORS = {
    'let': CYAN, 'if': CYAN, 'else': CYAN, 'while': CYAN,
    'fun': CYAN, 'return': CYAN, 'print': CYAN,
    'NUMBER': GREEN, 'STRING': YELLOW,
    'ID': WHITE,
    'ASSIGN': MAGENTA, 'EQ': MAGENTA, 'NEQ': MAGENTA,
    'LT': MAGENTA, 'GT': MAGENTA, 'LE': MAGENTA, 'GE': MAGENTA,
    'PLUS': WHITE, 'MINUS': WHITE, 'MUL': WHITE,
    'DIV': WHITE, 'MOD': WHITE,
    'LPAREN': DIM, 'RPAREN': DIM,
    'LBRACE': DIM, 'RBRACE': DIM,
    'SEMICOLON': DIM, 'COMMA': DIM,
}

def colour_token(tok):
    c = TOKEN_COLORS.get(tok.type, WHITE)
    return col(tok.type, c)

# ── TAC syntax highlighting ──────────────────────────────────

def highlight_tac(line):
    import re
    # Labels
    if re.match(r'^L\d+:$', line.strip()):
        return col(line, MAGENTA)
    # Keywords
    line = re.sub(r'\b(FUNC_BEGIN|FUNC_END|IF_FALSE|GOTO|RETURN|PRINT|PARAM|CALL)\b',
                  lambda m: col(m.group(), CYAN), line)
    # Temp variables
    line = re.sub(r'\b(t\d+)\b', lambda m: col(m.group(), YELLOW), line)
    # Numbers
    line = re.sub(r'\b(\d+\.?\d*)\b', lambda m: col(m.group(), GREEN), line)
    # Labels in jumps
    line = re.sub(r'\b(L\d+)\b', lambda m: col(m.group(), MAGENTA), line)
    return line

# ════════════════════════════════════════════════════════════
#  MAIN COMPILER PIPELINE
# ════════════════════════════════════════════════════════════

def compile_and_run(source, show_ast=False):

    print(f'\n{col("█" * 62, CYAN)}')
    print(col('  SIMPLE MINI COMPILER  —  All 6 Phases', BOLD + WHITE))
    print(col('█' * 62, CYAN))

    # ── PHASE 1: LEXICAL ANALYSIS ────────────────────────────
    header('PHASE 1 — LEXICAL ANALYSIS  (Tokenizer)')

    lexer  = Lexer(source)
    tokens = lexer.tokenize()

    # Remove EOF from display
    display_tokens = [t for t in tokens if t.type != 'EOF']

    # Print tokens in a nice table
    print(f'\n  {"TYPE":<18} {"VALUE":<20} {"LINE"}')
    print(f'  {col(LINE, DIM)}')
    for tok in display_tokens:
        c = TOKEN_COLORS.get(tok.type, WHITE)
        print(f'  {col(tok.type, c):<28} {col(str(tok.value), WHITE):<20} {col(str(tok.line), DIM)}')

    print(f'\n  {col(str(len(display_tokens)), GREEN)} tokens found', end='')
    if lexer.errors:
        print()
        for e in lexer.errors:
            err(e)
    else:
        print(col('  ✔  No errors', GREEN))

    if lexer.errors:
        print(col('\n  Compilation stopped.', RED))
        return

    # ── PHASE 2: SYNTAX ANALYSIS ─────────────────────────────
    header('PHASE 2 — SYNTAX ANALYSIS  (Parser → AST)')

    parser = Parser(tokens)
    ast    = parser.parse()

    if show_ast:
        import json
        print(f'\n  {bold("Abstract Syntax Tree (AST):")}')
        print(col('  ' + json.dumps(ast, indent=4).replace('\n', '\n  '), DIM))
    else:
        # Print a human-readable summary of the AST
        print(f'\n  {bold("AST Summary:")}')
        for stmt in ast['body']:
            _print_ast_node(stmt, indent=2)

    if parser.errors:
        print()
        for e in parser.errors:
            err(e)
        print(col('\n  Compilation stopped.', RED))
        return
    else:
        print()
        ok('AST built successfully — no syntax errors')

    # ── PHASE 3: SEMANTIC ANALYSIS ───────────────────────────
    header('PHASE 3 — SEMANTIC ANALYSIS  (Type & Scope Checking)')
    print()

    analyzer = SemanticAnalyzer()
    sem_errors = analyzer.analyze(ast)

    # Print symbol table
    print(f'  {bold("Symbol Table:")}')
    print(f'  {"NAME":<20} {"KIND":<10} {"PARAMS"}')
    print(f'  {col(LINE, DIM)}')
    for scope in analyzer.table.scopes:
        for name, info in scope.items():
            kind = info.get('kind', '?')
            params = ', '.join(info.get('params', [])) if kind == 'fun' else '—'
            c = CYAN if kind == 'fun' else WHITE
            print(f'  {col(name, c):<30} {col(kind, YELLOW):<20} {col(params, DIM)}')

    print()
    if sem_errors:
        for e in sem_errors:
            err(e)
        print(col('\n  Compilation stopped.', RED))
        return
    else:
        ok('No semantic errors — all variables and functions are valid')

    # ── PHASE 4: INTERMEDIATE CODE GENERATION ───────────────
    header('PHASE 4 — INTERMEDIATE CODE GENERATION  (Three-Address Code)')

    cg  = CodeGenerator()
    tac = cg.generate(ast)

    print(f'\n  {bold("Generated TAC Instructions:")}')
    print(f'  {col(LINE, DIM)}')
    for i, line in enumerate(tac, 1):
        print(f'  {col(str(i).rjust(3), DIM)}  {highlight_tac(line)}')

    print(f'\n  {col(str(len(tac)), GREEN)} TAC instructions generated')

    # ── PHASE 5: OPTIMIZATION ────────────────────────────────
    header('PHASE 5 — OPTIMIZATION')

    opt     = Optimizer(tac)
    opt_tac = opt.optimize()
    removed = len(tac) - len(opt_tac)

    print(f'\n  {bold("Optimized TAC:")}')
    print(f'  {col(LINE, DIM)}')
    for i, line in enumerate(opt_tac, 1):
        print(f'  {col(str(i).rjust(3), DIM)}  {highlight_tac(line)}')

    print()
    if removed > 0:
        ok(f'{removed} instruction(s) eliminated by optimizer')
    else:
        ok('Code is already optimal — no changes needed')

    print()
    techniques = [
        'Constant Folding    →  5 + 3 becomes 8 directly',
        'Constant Propagation→  known values substituted inline',
        'Strength Reduction  →  x*1 → x,  x*0 → 0,  x*2 → x+x',
        'Dead Code Elim.     →  unused temporaries removed',
        'CSE                 →  duplicate computations reused',
    ]
    for t in techniques:
        info_line(t)

    # ── PHASE 6: VIRTUAL MACHINE EXECUTION ──────────────────
    header('PHASE 6 — VIRTUAL MACHINE EXECUTION  (Output)')

    vm     = VirtualMachine(opt_tac)
    output = vm.run()

    print()
    if output:
        for line in output:
            print(f'  {col("►", GREEN)} {bold(col(line, WHITE))}')
    else:
        print(f'  {col("(no output produced)", DIM)}')

    print(f'\n{col(DLINE, CYAN)}')
    print(col('  COMPILATION & EXECUTION COMPLETE', BOLD + GREEN))
    print(col(DLINE, CYAN) + '\n')

    return output


# ── Human-readable AST printer ───────────────────────────────

def _print_ast_node(node, indent=0):
    pad = '  ' * indent
    kind = node.get('kind', '?')

    if kind == 'Fun':
        params = ', '.join(node.get('params', []))
        print(f'{pad}{col("fun", CYAN)} {col(node["name"], WHITE)}({col(params, YELLOW)})')
        for s in node.get('body', []):
            _print_ast_node(s, indent + 1)

    elif kind == 'Let':
        print(f'{pad}{col("let", CYAN)} {col(node["name"], WHITE)} = {_expr_str(node["value"])}')

    elif kind == 'Assign':
        print(f'{pad}{col(node["name"], WHITE)} = {_expr_str(node["value"])}')

    elif kind == 'If':
        print(f'{pad}{col("if", CYAN)} ({_expr_str(node["cond"])})')
        for s in node.get('then', []):
            _print_ast_node(s, indent + 1)
        if node.get('else_'):
            print(f'{pad}{col("else", CYAN)}')
            for s in node['else_']:
                _print_ast_node(s, indent + 1)

    elif kind == 'While':
        print(f'{pad}{col("while", CYAN)} ({_expr_str(node["cond"])})')
        for s in node.get('body', []):
            _print_ast_node(s, indent + 1)

    elif kind == 'Return':
        print(f'{pad}{col("return", CYAN)} {_expr_str(node["value"])}')

    elif kind == 'Print':
        print(f'{pad}{col("print", CYAN)}({_expr_str(node["value"])})')

    elif kind == 'ExprStmt':
        print(f'{pad}{_expr_str(node["expr"])}')

    else:
        print(f'{pad}{col(kind, DIM)}')


def _expr_str(expr):
    k = expr.get('kind')
    if k == 'Num':    return col(str(expr['value']), GREEN)
    if k == 'Str':    return col(f'"{expr["value"]}"', YELLOW)
    if k == 'Var':    return col(expr['name'], WHITE)
    if k == 'Unary':  return f'{col("-", MAGENTA)}{_expr_str(expr["expr"])}'
    if k == 'BinOp':  return f'{_expr_str(expr["left"])} {col(expr["op"], MAGENTA)} {_expr_str(expr["right"])}'
    if k == 'Call':
        args = ', '.join(_expr_str(a) for a in expr.get('args', []))
        return f'{col(expr["name"], CYAN)}({args})'
    return col('?', RED)


# ════════════════════════════════════════════════════════════
#  DEMO PROGRAMS  —  written in our simple language
# ════════════════════════════════════════════════════════════

DEMOS = {

'factorial': """\
# Recursive factorial function
fun factorial(n) {
    if (n == 0) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

let result = factorial(5);
print(result);
""",

'fibonacci': """\
# Recursive fibonacci
fun fib(n) {
    if (n <= 1) {
        return n;
    } else {
        return fib(n - 1) + fib(n - 2);
    }
}

let f = fib(8);
print(f);
""",

'arithmetic': """\
# Basic arithmetic with optimizer test
let a = 10;
let b = 5 + 3;        # constant folding: becomes 8
let c = a + b * 2;    # strength reduction: *2 → +
print(c);
""",

'if_else': """\
# If-else condition
let x = 15;
if (x > 10) {
    let result = x * 2;
    print(result);
} else {
    print(x);
}
""",

'while_loop': """\
# While loop: sum 1 to 5
let i = 1;
let sum = 0;
while (i <= 5) {
    sum = sum + i;
    i = i + 1;
}
print(sum);
""",

'scope_test': """\
# Variable scope + multiple functions
fun square(n) {
    return n * n;
}

fun cube(n) {
    return n * square(n);
}

let a = square(4);
let b = cube(3);
print(a);
print(b);
""",

}


# ════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Simple Mini Compiler — All 6 Phases',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f'Available demos: {", ".join(DEMOS.keys())}'
    )
    ap.add_argument('--demo', choices=list(DEMOS.keys()), default='factorial',
                    help='Run a built-in demo program')
    ap.add_argument('--file', help='Compile and run a source file (.txt or .lang)')
    ap.add_argument('--ast',  action='store_true',
                    help='Show full JSON AST instead of summary')
    args = ap.parse_args()

    if args.file:
        with open(args.file) as f:
            source = f.read()
        print(f'\n  {col("Source file:", BOLD)} {args.file}')
    else:
        source = DEMOS[args.demo]
        print(f'\n  {col("Demo:", BOLD)} {args.demo}')
        print(f'  {col("Source code:", BOLD)}')
        print(f'  {col(LINE, DIM)}')
        for line in source.strip().splitlines():
            print(f'  {col(line, DIM)}')

    compile_and_run(source, show_ast=args.ast)
