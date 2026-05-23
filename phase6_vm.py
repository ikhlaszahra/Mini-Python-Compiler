# ════════════════════════════════════════════════════════════
#  PHASE 6 — VIRTUAL MACHINE EXECUTION
#  Reads the optimized TAC line by line and executes it.
#  Uses a simple stack to handle function calls.
# ════════════════════════════════════════════════════════════

import re


class ReturnSignal(Exception):
    """Used to unwind the call stack when RETURN is hit."""
    def __init__(self, value):
        self.value = value


class VirtualMachine:

    def __init__(self, tac):
        self.code      = tac
        self.output    = []       # collected PRINT results
        self.memory    = {}       # global variables
        self.functions = {}       # name → {start, end, params}
        self.labels    = {}       # label name → code index
        self._params   = []       # staging area for PARAM before CALL
        self._index()

    # ── Pre-scan: find all labels and function boundaries ────

    def _index(self):
        for i, line in enumerate(self.code):
            line = line.strip()
            # Label   "L3:"
            if re.match(r'^L\d+:$', line):
                self.labels[line[:-1]] = i
            # Function start   "FUNC_BEGIN fact(n)"
            m = re.match(r'^FUNC_BEGIN\s+(\w+)\(([^)]*)\)$', line)
            if m:
                name   = m.group(1)
                params = [p.strip() for p in m.group(2).split(',') if p.strip()]
                self.functions[name] = {'start': i, 'params': params}
            # Function end
            m2 = re.match(r'^FUNC_END\s+(\w+)$', line)
            if m2:
                self.functions[m2.group(1)]['end'] = i

    # ── Main execution (global scope) ────────────────────────

    def run(self):
        pc = 0
        while pc < len(self.code):
            line = self.code[pc].strip()
            pc  += 1

            if not line or re.match(r'^L\d+:$', line):
                continue

            # Skip over function bodies in the global pass
            if line.startswith('FUNC_BEGIN'):
                m = re.match(r'^FUNC_BEGIN\s+(\w+)', line)
                if m and m.group(1) in self.functions:
                    pc = self.functions[m.group(1)]['end'] + 1
                continue

            if line.startswith('FUNC_END'):
                continue

            pc = self._exec(line, pc, self.memory)

        return self.output

    # ── Execute one TAC instruction ───────────────────────────

    def _exec(self, line, pc, env):
        """Execute one instruction.  env is the current variable scope."""

        # PRINT val
        if line.startswith('PRINT '):
            val = self._resolve(line[6:].strip(), env)
            # Show int if possible
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            self.output.append(str(val))
            return pc

        # GOTO label
        m = re.match(r'^GOTO\s+(L\d+)$', line)
        if m:
            return self.labels[m.group(1)] + 1

        # IF_FALSE cond GOTO label
        m = re.match(r'^IF_FALSE\s+(.+)\s+GOTO\s+(L\d+)$', line)
        if m:
            cond = self._resolve(m.group(1).strip(), env)
            if not cond:
                return self.labels[m.group(2)] + 1
            return pc

        # PARAM val  (push argument for upcoming CALL)
        m = re.match(r'^PARAM\s+(.+)$', line)
        if m:
            self._params.append(self._resolve(m.group(1).strip(), env))
            return pc

        # dest = CALL name, n
        m = re.match(r'^(\w+)\s*=\s*CALL\s+(\w+),\s*(\d+)$', line)
        if m:
            dest  = m.group(1)
            fname = m.group(2)
            nargs = int(m.group(3))
            args  = self._params[-nargs:] if nargs else []
            del self._params[-nargs:]
            result = self._call(fname, args)
            env[dest]         = result
            self.memory[dest] = result
            return pc

        # RETURN val  (raises signal)
        m = re.match(r'^RETURN\s+(.+)$', line)
        if m:
            val = self._resolve(m.group(1).strip(), env)
            raise ReturnSignal(val)

        # dest = rhs  (assignment)
        m = re.match(r'^(\w+)\s*=\s*(.+)$', line)
        if m:
            dest = m.group(1)
            val  = self._eval(m.group(2).strip(), env)
            env[dest]         = val
            self.memory[dest] = val
            return pc

        return pc

    # ── Call a user-defined function ─────────────────────────

    def _call(self, name, args):
        if name not in self.functions:
            raise RuntimeError(f'[VM Error] Undefined function: {name}')

        fi     = self.functions[name]
        local  = {}
        for param, val in zip(fi['params'], args):
            local[param] = val

        pc  = fi['start'] + 1
        end = fi['end']
        ret = 0

        try:
            while pc <= end:
                line = self.code[pc].strip()
                pc  += 1
                if not line or re.match(r'^L\d+:$', line):
                    continue
                if line.startswith('FUNC_BEGIN') or line.startswith('FUNC_END'):
                    continue
                pc = self._exec(line, pc, local)
        except ReturnSignal as sig:
            ret = sig.value

        return ret

    # ── Resolve a single token to a value ────────────────────

    def _resolve(self, token, env):
        token = token.strip()
        # String literal
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        # Number literal
        try:
            return float(token) if '.' in token else int(token)
        except ValueError:
            pass
        # Variable: check local scope first, then global
        if token in env:
            return env[token]
        if token in self.memory:
            return self.memory[token]
        return 0

    # ── Evaluate a RHS expression string ─────────────────────

    def _eval(self, rhs, env):
        rhs = rhs.strip()

        # Unary negation
        m = re.match(r'^-(\w+)$', rhs)
        if m:
            return -self._resolve(m.group(1), env)

        # Binary operation
        m = re.match(r'^(.+?)\s*([+\-*/%]|==|!=|<=|>=|<|>)\s*(.+)$', rhs)
        if m:
            left  = self._resolve(m.group(1).strip(), env)
            op    = m.group(2)
            right = self._resolve(m.group(3).strip(), env)
            ops = {
                '+':  lambda a, b: a + b,
                '-':  lambda a, b: a - b,
                '*':  lambda a, b: a * b,
                '/':  lambda a, b: a / b if b != 0 else 0,
                '%':  lambda a, b: a % b if b != 0 else 0,
                '==': lambda a, b: int(a == b),
                '!=': lambda a, b: int(a != b),
                '<':  lambda a, b: int(a <  b),
                '>':  lambda a, b: int(a >  b),
                '<=': lambda a, b: int(a <= b),
                '>=': lambda a, b: int(a >= b),
            }
            if op in ops:
                return ops[op](left, right)

        return self._resolve(rhs, env)
