# ════════════════════════════════════════════════════════════
#  PHASE 5 — OPTIMIZATION
#  Makes the TAC shorter / faster without changing the result
#
#  Techniques applied:
#  1. Constant Folding        →  t1 = 5 + 3      becomes  t1 = 8
#  2. Constant Propagation    →  x = 8; t2 = x+1 becomes  t2 = 8+1 → t2 = 9
#  3. Strength Reduction      →  x * 1 → x,  x * 0 → 0,  x * 2 → x+x
#  4. Dead Code Elimination   →  removes temps never used again
#  5. CSE (Common Subexpr.)   →  if same calc done twice, reuse result
# ════════════════════════════════════════════════════════════

import re


class Optimizer:

    def __init__(self, tac):
        self.code = list(tac)

    def optimize(self):
        # Run multiple passes until no more changes
        for _ in range(3):
            self.code = self._constant_folding(self.code)
            self.code = self._constant_propagation(self.code)
            self.code = self._strength_reduction(self.code)
            self.code = self._cse(self.code)
            self.code = self._dead_code_elimination(self.code)
        return self.code

    # ── 1. Constant Folding ──────────────────────────────────
    # If both sides of an operation are numbers, compute it now.

    def _constant_folding(self, code):
        result = []
        pat = re.compile(r'^(\w+)\s*=\s*(-?\d+\.?\d*)\s*([+\-*/%])\s*(-?\d+\.?\d*)$')
        for line in code:
            m = pat.match(line)
            if m:
                dest = m.group(1)
                a    = float(m.group(2))
                op   = m.group(3)
                b    = float(m.group(4))
                try:
                    val = {
                        '+': a + b, '-': a - b,
                        '*': a * b, '/': a / b if b != 0 else None,
                        '%': a % b if b != 0 else None,
                    }[op]
                    if val is not None:
                        # Display as int if possible
                        display = int(val) if val == int(val) else round(val, 6)
                        result.append(f'{dest} = {display}')
                        continue
                except Exception:
                    pass
            result.append(line)
        return result

    # ── 2. Constant Propagation ──────────────────────────────
    # If  x = 5  is known, replace uses of x with 5.

    def _constant_propagation(self, code):
        known = {}
        result = []
        num_pat = re.compile(r'^-?\d+\.?\d*$')

        for line in code:
            # Reset at function boundaries
            if line.startswith('FUNC_BEGIN') or line.startswith('FUNC_END'):
                known.clear()
                result.append(line)
                continue

            # Substitute known constants on the right-hand side
            def replace_known(token):
                token = token.strip()
                return known[token] if token in known else token

            # Try to substitute tokens in the RHS
            if '=' in line and not line.strip().endswith(':'):
                lhs, _, rhs = line.partition('=')
                lhs = lhs.strip()
                rhs = rhs.strip()
                # Replace each word token in rhs
                new_rhs = re.sub(
                    r'\b([a-zA-Z_]\w*)\b',
                    lambda m: known.get(m.group(1), m.group(1)),
                    rhs
                )
                line = f'{lhs} = {new_rhs}'

                # Record if LHS is now assigned a plain constant
                rhs_clean = new_rhs.strip()
                if num_pat.match(rhs_clean):
                    known[lhs] = rhs_clean
                elif lhs in known:
                    del known[lhs]

            result.append(line)
        return result

    # ── 3. Strength Reduction ────────────────────────────────
    # Replace expensive ops with cheaper ones.

    def _strength_reduction(self, code):
        result = []
        for line in code:
            # x * 1  →  x
            m = re.match(r'^(\w+)\s*=\s*(\w+)\s*\*\s*1$', line)
            if m:
                result.append(f'{m.group(1)} = {m.group(2)}')
                continue
            # x * 0  →  0
            m = re.match(r'^(\w+)\s*=\s*(\w+)\s*\*\s*0$', line)
            if m:
                result.append(f'{m.group(1)} = 0')
                continue
            # 0 * x  →  0
            m = re.match(r'^(\w+)\s*=\s*0\s*\*\s*(\w+)$', line)
            if m:
                result.append(f'{m.group(1)} = 0')
                continue
            # x * 2  →  x + x
            m = re.match(r'^(\w+)\s*=\s*(\w+)\s*\*\s*2$', line)
            if m:
                result.append(f'{m.group(1)} = {m.group(2)} + {m.group(2)}')
                continue
            # x / 1  →  x
            m = re.match(r'^(\w+)\s*=\s*(\w+)\s*/\s*1$', line)
            if m:
                result.append(f'{m.group(1)} = {m.group(2)}')
                continue
            # x + 0  or  0 + x  →  x
            m = re.match(r'^(\w+)\s*=\s*(\w+)\s*\+\s*0$', line)
            if m:
                result.append(f'{m.group(1)} = {m.group(2)}')
                continue
            m = re.match(r'^(\w+)\s*=\s*0\s*\+\s*(\w+)$', line)
            if m:
                result.append(f'{m.group(1)} = {m.group(2)}')
                continue
            result.append(line)
        return result

    # ── 4. Dead Code Elimination ─────────────────────────────
    # Remove assignments to temp variables that are never read.

    def _dead_code_elimination(self, code):
        # Count how many times each temp is READ (appears on RHS)
        used = set()
        for line in code:
            parts = line.split('=', 1)
            rhs = parts[1] if len(parts) > 1 else line
            for tok in re.findall(r'\bt\d+\b', rhs):
                used.add(tok)
            # Anything on a non-assignment line is used
            if '=' not in line:
                for tok in re.findall(r'\bt\d+\b', line):
                    used.add(tok)

        result = []
        for line in code:
            m = re.match(r'^(t\d+)\s*=', line)
            if m and m.group(1) not in used:
                continue    # dead — drop it
            result.append(line)
        return result

    # ── 5. Common Subexpression Elimination (CSE) ────────────
    # If the same computation appears twice, reuse the first result.

    def _cse(self, code):
        seen   = {}     # rhs → temp that holds the result
        result = []
        for line in code:
            if line.startswith('FUNC_BEGIN') or line.startswith('FUNC_END'):
                seen.clear()
                result.append(line)
                continue
            m = re.match(r'^(t\d+)\s*=\s*(.+)$', line)
            if m:
                dest = m.group(1)
                rhs  = m.group(2).strip()
                if rhs in seen:
                    result.append(f'{dest} = {seen[rhs]}')
                    continue
                seen[rhs] = dest
            result.append(line)
        return result
