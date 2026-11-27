"""C code generation (GNU C11, compiled with gcc)."""

from __future__ import annotations

import json

from .checker import IO_BUILTINS, Checker
from .errors import CompileError, Diag
from .nodes import (
    ArrayLit, Assign, Binary, Block, Bool, Break, Call, Continue, Expr, ExprStmt,
    Field, Float, FnDef, For, If, Index, Int, Let, Match, Name, Program, Ret, Stmt, Str,
    StructLit, TestDef, Try, Type, Unary, Variant, While, subst,
)
from .parser import show
from .runtime import ARRAY_TEMPLATE, RUNTIME

PRIM_C = {"i64": "int64_t", "f64": "double", "bool": "bool", "str": "const char *", "unit": "void"}
MAX_INSTANCES = 500

CMP = {"==", "!=", "<", "<=", ">", ">="}
ARITH_FN = {"+": "aim_add", "-": "aim_sub", "*": "aim_mul", "/": "aim_div", "%": "aim_mod"}


def mangle(t: Type) -> str:
    if isinstance(t, tuple):
        k = t[0]
        if k in ("arr", "opt", "res"):
            return {"arr": "A_", "opt": "O_", "res": "R_"}[k] + mangle(t[1])
        if k == "tp":
            raise AssertionError(f"unsubstituted type parameter {t[1]}")
        return ("S_" if k == "struct" else "E_") + t[1]
    return {"i64": "i", "f64": "f", "bool": "b", "str": "s"}[t]


def ctype(t: Type) -> str:
    if isinstance(t, tuple):
        return f"{mangle(t)} *" if t[0] == "arr" else mangle(t)
    return PRIM_C[t]


def c_str(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\{ord(ch):03o}")
        else:
            out.append(ch)
    # split after octal/hex-looking sequences is unnecessary: we only emit 3-digit octal
    return '"' + "".join(out) + '"'


class Gen:
    def __init__(self, prog: Program, chk: Checker, checked: bool = True):
        self.prog = prog
        self.chk = chk
        self.checked = checked
        self.out: list[str] = []
        self.ind = 0
        self.tmp = 0
        self.fn: FnDef | None = None
        self.sub: dict[str, Type] = {}      # type parameters of the fn instance being generated
        self.used: dict[str, Type] = {}     # every compound C type the program needs, by mangled name
        self.protos: list[str] = []
        self.instances: dict[str, tuple[FnDef, dict[str, Type]]] = {}
        self.pending: list[str] = []

    # ---------- types ----------

    def T(self, t: Type) -> Type:
        """Concrete type in the current fn instance; registers it for emission."""
        t = subst(t, self.sub)
        self.need(t)
        return t

    def need(self, t: Type):
        if not isinstance(t, tuple):
            return
        m = mangle(t)
        if m in self.used:
            return
        self.used[m] = t
        if t[0] in ("arr", "opt", "res"):
            self.need(t[1])
        for c in self.chk.components(t):
            self.need(c)

    def c(self, t: Type) -> str:
        return ctype(self.T(t))

    def m(self, t: Type) -> str:
        return mangle(self.T(t))

    def emit(self, s: str):
        self.out.append("    " * self.ind + s)

    def fresh(self, base: str = "t") -> str:
        self.tmp += 1
        return f"__{base}{self.tmp}"

    # ---------- effects (for evaluation order) ----------

    def has_io(self, e: Expr) -> bool:
        if isinstance(e, Call):
            if e.name in IO_BUILTINS:
                return True
            fn = self.chk.fns.get(e.name)
            if fn and "io" in fn.effects:
                return True
            return any(self.has_io(a.expr) for a in e.args)
        if isinstance(e, Binary):
            return self.has_io(e.left) or self.has_io(e.right)
        if isinstance(e, Unary):
            return self.has_io(e.operand)
        if isinstance(e, Index):
            return self.has_io(e.base) or self.has_io(e.index)
        if isinstance(e, Field):
            return self.has_io(e.base)
        if isinstance(e, StructLit):
            return any(self.has_io(v) for _, v, _, _ in e.fields)
        if isinstance(e, ArrayLit):
            return any(self.has_io(v) for v in e.elems)
        if isinstance(e, Variant):
            return any(self.has_io(v) for v in e.args or [])
        if isinstance(e, Try):
            return self.has_io(e.operand)
        return False

    def ordered(self, exprs: list[Expr]) -> bool:
        """True when C's unspecified argument order could change behaviour."""
        return sum(1 for x in exprs if self.has_io(x)) >= 2

    # ---------- program ----------

    def program(self, mode: str) -> str:
        for fn in self.prog.fns:
            if not fn.tparams:
                self.function(fn, {})
        if mode == "test":
            for t in self.prog.tests:
                self.test(t)
            self.test_main()
        else:
            self.out.append("int main(int argc, char **argv) {")
            self.out.append("    aim_argc = argc; aim_argv = argv; aim_out = stdout;")
            self.out.append("    f_main();")
            self.out.append("    return 0;")
            self.out.append("}")
        while self.pending:  # generic instances, found while generating the code above
            fn, sub = self.instances[self.pending.pop()]
            self.function(fn, sub)
        head = [RUNTIME] + self.types() + [p + ";" for p in self.protos] + [""]
        return "\n".join(head + self.out) + "\n"

    def types(self) -> list[str]:
        out: list[str] = []
        used = list(self.used.values())
        for t in used:
            out.append(f"typedef struct {mangle(t)} {mangle(t)};")
        for t in used:
            if t[0] == "arr":
                out.append(f"struct {mangle(t)} {{ int64_t len, cap; {ctype(t[1])} *data; }};")
        done: set[str] = set()

        def emit(t: Type):  # by-value members first
            m = mangle(t)
            if m in done or t[0] == "arr":
                return
            done.add(m)
            for c in self.chk.components(t):
                if isinstance(c, tuple):
                    emit(c)
            if t[0] == "struct":
                fields = " ".join(f"{ctype(ft)} f_{fn};" for fn, ft, _, _ in self.chk.structs[t[1]].fields)
                out.append(f"struct {m} {{ {fields} }};")
                return
            arms = []
            for vn, ps in self.chk.variants(t):
                if ps:
                    arms.append("struct { " + " ".join(f"{ctype(p)} _{i};" for i, p in enumerate(ps)) + f" }} u_{vn};")
            union = f" union {{ {' '.join(arms)} }};" if arms else ""
            out.append(f"struct {m} {{ int32_t tag;{union} }};")

        for t in used:
            emit(t)
        for t in used:
            m, ct = mangle(t), ctype(t)
            out.append(f"static {ct} copy_{m}({ct} s);")
            if self.chk.comparable(t):
                out.append(f"static bool eq_{m}({ct} a, {ct} b);")
                out.append(f"static void sbf_{m}(aim_sb *b, {ct} v);")
        for t in used:
            out.extend(self.helpers(t))
            if t[0] != "arr" and self.chk.comparable(t):
                m = mangle(t)
                out.append(f"static void aim_fmt_{m}(char *p, size_t n, {m} v) "
                           f"{{ aim_sb b = {{p, n, 0}}; p[0] = 0; sbf_{m}(&b, v); }}")
        return out

    def helpers(self, t: Type) -> list[str]:
        m, ct = mangle(t), ctype(t)
        if t[0] == "arr":
            et = t[1]
            return [ARRAY_TEMPLATE.format(m=mangle(et), et=ctype(et), copy_v=self.copy_of("v", et),
                                          copy_elem=self.copy_of("s->data[i]", et))]
        out = []
        if t[0] == "struct":
            fields = self.chk.structs[t[1]].fields
            parts = [f"r.f_{fn} = {self.copy_of('s.f_' + fn, ft)};" for fn, ft, _, _ in fields if self.chk.heavy(ft)]
            out.append(f"static {ct} copy_{m}({ct} s) {{ {ct} r = s; {' '.join(parts)} return r; }}")
            if self.chk.comparable(t):
                eqs = " && ".join(self.eq_of(f"a.f_{fn}", f"b.f_{fn}", ft) for fn, ft, _, _ in fields) or "true"
                out.append(f"static bool eq_{m}({ct} a, {ct} b) {{ return {eqs}; }}")
                body = [f'sb_put(b, "{t[1]}{{");']
                for i, (fn, ft, _, _) in enumerate(fields):
                    body.append(f'sb_put(b, "{", " if i else ""}{fn}: "); {self.sbf_of("v.f_" + fn, ft)}')
                body.append('sb_put(b, "}");')
                out.append(f"static void sbf_{m}(aim_sb *b, {ct} v) {{ {' '.join(body)} }}")
            return out
        vs = self.chk.variants(t)
        prefix = f"{t[1]}." if t[0] == "enum" else ""
        cases = []
        for i, (vn, ps) in enumerate(vs):
            parts = [f"r.u_{vn}._{j} = {self.copy_of(f's.u_{vn}._{j}', p)};" for j, p in enumerate(ps) if self.chk.heavy(p)]
            if parts:
                cases.append(f"case {i}: {' '.join(parts)} break;")
        sw = f"switch (s.tag) {{ {' '.join(cases)} }} " if cases else ""
        out.append(f"static {ct} copy_{m}({ct} s) {{ {ct} r = s; {sw}return r; }}")
        if self.chk.comparable(t):
            ecases, fcases = [], []
            for i, (vn, ps) in enumerate(vs):
                eq = " && ".join(self.eq_of(f"a.u_{vn}._{j}", f"b.u_{vn}._{j}", p) for j, p in enumerate(ps)) or "true"
                ecases.append(f"case {i}: return {eq};")
                f = [f'sb_put(b, "{prefix}{vn}{"(" if ps else ""}");']
                for j, p in enumerate(ps):
                    f.append(('sb_put(b, ", "); ' if j else "") + self.sbf_of(f"v.u_{vn}._{j}", p))
                if ps:
                    f.append('sb_put(b, ")");')
                fcases.append(f"case {i}: {' '.join(f)} break;")
            out.append(f"static bool eq_{m}({ct} a, {ct} b) {{ if (a.tag != b.tag) return false; "
                       f"switch (a.tag) {{ {' '.join(ecases)} }} return true; }}")
            out.append(f"static void sbf_{m}(aim_sb *b, {ct} v) {{ switch (v.tag) {{ {' '.join(fcases)} }} }}")
        return out

    def eq_of(self, a: str, b: str, t: Type) -> str:
        if t == "str":
            return f"(strcmp({a}, {b}) == 0)"
        if isinstance(t, tuple):
            return f"eq_{mangle(t)}({a}, {b})"
        return f"({a} == {b})"

    def sbf_of(self, v: str, t: Type) -> str:
        return f"sbf_{t if not isinstance(t, tuple) else mangle(t)}(b, {v});"

    def copy_of(self, c: str, t: Type) -> str:
        t = self.T(t)
        if not self.chk.heavy(t):
            return c
        return f"copy_{mangle(t)}({c})"

    # ---------- functions ----------

    def fname(self, fn: FnDef, sub: dict[str, Type]) -> str:
        if not fn.tparams:
            return f"f_{fn.name}"
        return f"f_{fn.name}__" + "__".join(mangle(sub[tp]) for tp in fn.tparams)

    def instance(self, fn: FnDef, targs: list[Type]) -> str:
        sub = dict(zip(fn.tparams, targs))
        name = self.fname(fn, sub)
        if name not in self.instances:
            if len(self.instances) >= MAX_INSTANCES:
                raise CompileError([Diag("E714", f"generic fn '{fn.name}' needs more than {MAX_INSTANCES} instances "
                                         "(a generic fn calls itself with a growing type)", fn.line, fn.col)])
            self.instances[name] = (fn, sub)
            self.pending.append(name)
        return name

    def proto(self, fn: FnDef) -> str:
        ps = []
        for p in fn.params:
            ps.append(f"{self.c(p.ty)}{'*' if p.mut else ''} v_{p.name}")
        return f"static {self.c(fn.ret)} {self.fname(fn, self.sub)}({', '.join(ps) or 'void'})"

    def function(self, fn: FnDef, sub: dict[str, Type]):
        self.fn = fn
        self.sub = sub
        self.protos.append(self.proto(fn))
        self.out.append(self.proto(fn) + " {")
        self.ind = 1
        contracts = self.checked
        if contracts:
            for r in fn.requires:
                self.emit(f"if (!({self.expr(r)})) aim_fail(\"requires\", "
                          f"{c_str(f'precondition of {fn.name} failed: {show(r)}')}, {r.line}, {r.col}, 0, 0, 0);")
        self.use_ensures = contracts and bool(fn.ensures)
        if self.use_ensures and fn.ret != "unit":
            self.emit(f"{self.c(fn.ret)} __result;")
        self.block_body(fn.body)
        if self.use_ensures:
            self.out.append("__ensure:;")
            for e in fn.ensures:
                self.emit(f"if (!({self.expr(e)})) aim_fail(\"ensures\", "
                          f"{c_str(f'postcondition of {fn.name} failed: {show(e)}')}, {e.line}, {e.col}, 0, 0, 0);")
            if fn.ret != "unit":
                self.emit("return __result;")
        elif fn.ret != "unit":
            self.emit("__builtin_unreachable();")
        self.ind = 0
        self.out.append("}")
        self.out.append("")
        self.fn = None
        self.sub = {}

    def test(self, t: TestDef):
        self.use_ensures = False
        self.protos.append(f"static void t_{t.name}(void)")
        self.out.append(f"static void t_{t.name}(void) {{")
        self.ind = 1
        self.block_body(t.body)
        self.ind = 0
        self.out.append("}")
        self.out.append("")

    def test_main(self):
        o = self.out
        o.append("int main(int argc, char **argv) {")
        o.append("    aim_argc = argc; aim_argv = argv; aim_out = stderr; aim_testing = 1;")
        o.append("    int passed = 0, failed = 0;")
        for t in self.prog.tests:
            name = json.dumps(t.name)
            o.append("    if (setjmp(aim_test_jmp) == 0) {")
            o.append(f"        t_{t.name}();")
            o.append(f"        printf(\"{{\\\"test\\\":%s,\\\"status\\\":\\\"pass\\\"}}\\n\", {c_str(name)}); passed++;")
            o.append("    } else {")
            o.append(f"        printf(\"{{\\\"test\\\":%s,\\\"status\\\":\\\"fail\\\",%s}}\\n\", {c_str(name)}, aim_fail_buf); failed++;")
            o.append("    }")
            o.append("    fflush(stdout);")
        o.append("    printf(\"{\\\"summary\\\":{\\\"passed\\\":%d,\\\"failed\\\":%d}}\\n\", passed, failed);")
        o.append("    return failed ? 1 : 0;")
        o.append("}")

    # ---------- statements ----------

    def block_body(self, b: Block):
        for s in b.stmts:
            self.stmt(s)

    def block(self, b: Block):
        self.ind += 1
        self.block_body(b)
        self.ind -= 1

    def stmt(self, s: Stmt):
        if isinstance(s, Let):
            t = s.ann if s.ann is not None else s.value.ty
            val = self.expr(s.value)
            if s.name == "_":
                self.emit(f"(void)({val});")
            else:
                self.emit(f"{self.c(t)} v_{s.name} = {val};")
        elif isinstance(s, Assign):
            tgt = self.place(s.target)
            val = self.expr(s.value)
            if s.op == "=":
                self.emit(f"{tgt} = {val};")
            else:
                op = s.op[0]
                if s.target.ty == "i64" and self.checked:
                    p = self.fresh("p")
                    self.emit(f"{{ int64_t *{p} = &({tgt}); *{p} = {ARITH_FN[op]}(*{p}, {val}, {s.line}, {s.col}); }}")
                else:
                    self.emit(f"{tgt} {s.op} {val};")
        elif isinstance(s, If):
            self.emit(f"if ({self.expr(s.cond)}) {{")
            self.block(s.then)
            cur = s
            while cur.els is not None:
                if getattr(cur.els, "is_elif", False):
                    nxt = cur.els.stmts[0]
                    assert isinstance(nxt, If)
                    self.emit(f"}} else if ({self.expr(nxt.cond)}) {{")
                    self.block(nxt.then)
                    cur = nxt
                else:
                    self.emit("} else {")
                    self.block(cur.els)
                    break
            self.emit("}")
        elif isinstance(s, While):
            self.emit(f"while ({self.expr(s.cond)}) {{")
            self.block(s.body)
            self.emit("}")
        elif isinstance(s, For):
            end = self.fresh("end")
            self.emit(f"for (int64_t v_{s.var} = {self.expr(s.start)}, {end} = {self.expr(s.stop)}; "
                      f"v_{s.var} < {end}; v_{s.var}++) {{")
            self.block(s.body)
            self.emit("}")
        elif isinstance(s, Ret):
            self.emit(self.ret_code(self.expr(s.value) if s.value is not None else None))
        elif isinstance(s, Match):
            self.match(s)
        elif isinstance(s, Break):
            self.emit("break;")
        elif isinstance(s, Continue):
            self.emit("continue;")
        elif isinstance(s, ExprStmt):
            if s.is_assert:
                self.assertion(s)
            else:
                self.emit(f"{self.expr(s.expr)};")
        else:
            raise AssertionError(type(s))

    def ret_code(self, val: str | None) -> str:
        if self.use_ensures:
            return f"{{ __result = {val}; goto __ensure; }}" if val is not None else "goto __ensure;"
        return f"return {val};" if val is not None else "return;"

    def match(self, s: Match):
        t = self.T(s.subject.ty)
        vs = self.chk.variants(t)
        mv = self.fresh("m")
        self.emit("{")
        self.ind += 1
        self.emit(f"{ctype(t)} {mv} = {self.expr(s.subject)};")
        covered = {a.tag for a in s.arms if a.tag is not None}
        exhaustive = len(covered) == len(vs) and all(a.variant is not None for a in s.arms)
        for i, arm in enumerate(s.arms):
            kw = "if" if i == 0 else "} else if"
            if arm.variant is None or (exhaustive and i == len(s.arms) - 1):
                self.emit("{" if i == 0 else "} else {")
            else:
                self.emit(f"{kw} ({mv}.tag == {arm.tag}) {{")
            self.ind += 1
            vn = vs[arm.tag][0] if arm.tag is not None else None
            for j, ((bname, _, _), pt) in enumerate(zip(arm.binds, arm.ptys)):
                if bname != "_":
                    self.emit(f"{self.c(pt)} v_{bname} = {mv}.u_{vn}._{j};")
            self.block_body(arm.body)
            self.ind -= 1
        if s.arms:
            self.emit("}")
        self.ind -= 1
        self.emit("}")

    def assertion(self, s: ExprStmt):
        e = s.expr
        src = c_str(show(e))
        lt_ = e.left.ty if isinstance(e, Binary) else None
        if isinstance(e, Binary) and e.op in CMP and (lt_ in ("i64", "f64", "bool", "str") or (
                e.op in ("==", "!=") and lt_ is not None and self.chk.comparable(lt_))):
            t = e.left.ty
            lt, rt = self.fresh("l"), self.fresh("r")
            self.emit("{")
            self.ind += 1
            self.emit(f"{self.c(t)} {lt} = {self.expr(e.left)};")
            self.emit(f"{self.c(t)} {rt} = {self.expr(e.right)};")
            if isinstance(t, tuple):
                cond = ("" if e.op == "==" else "!") + f"eq_{self.m(t)}({lt}, {rt})"
                fm = self.m(t)
            else:
                cond = f"strcmp({lt}, {rt}) {e.op} 0" if t == "str" else f"{lt} {e.op} {rt}"
                fm = t
            self.emit(f"if (!({cond})) {{")
            self.emit(f"    char lb[256], rb[256]; aim_fmt_{fm}(lb, sizeof lb, {lt}); aim_fmt_{fm}(rb, sizeof rb, {rt});")
            self.emit(f"    aim_fail(\"assert\", \"assertion failed\", {e.line}, {e.col}, {src}, lb, rb);")
            self.emit("}")
            self.ind -= 1
            self.emit("}")
        else:
            self.emit(f"if (!({self.expr(e)})) aim_fail(\"assert\", \"assertion failed\", {e.line}, {e.col}, {src}, 0, 0);")

    # ---------- expressions ----------

    def place(self, e: Expr) -> str:
        return self.expr(e)

    def expr(self, e: Expr) -> str:
        if isinstance(e, _Raw):
            return e.cname
        if e.ty is not None:
            self.T(e.ty)
        if isinstance(e, Int):
            if e.value == -(2**63):
                return "INT64_MIN"
            return f"INT64_C({e.value})"
        if isinstance(e, Float):
            r = repr(e.value)
            return r if ("." in r or "e" in r or "inf" in r or "nan" in r) else r + ".0"
        if isinstance(e, Bool):
            return "true" if e.value else "false"
        if isinstance(e, Str):
            return c_str(e.value)
        if isinstance(e, Name):
            return e.cname
        if isinstance(e, Unary):
            x = self.expr(e.operand)
            if e.op == "not":
                return f"(!{x})"
            if e.ty == "i64" and self.checked:
                return f"aim_neg({x}, {e.line}, {e.col})"
            return f"(-{x})"
        if isinstance(e, Binary):
            return self.binary(e)
        if isinstance(e, Index):
            b, i = self.expr(e.base), self.expr(e.index)
            m = self.m(e.ty)
            if self.checked:
                return f"(*A_{m}_at({b}, {i}, {e.line}, {e.col}))"
            return f"(({b})->data[{i}])"
        if isinstance(e, Field):
            return f"({self.expr(e.base)}).f_{e.name}"
        if isinstance(e, StructLit):
            parts = [f".f_{n} = {self.expr(v)}" for n, v, _, _ in e.fields]
            return f"((S_{e.name}){{{', '.join(parts)}}})"
        if isinstance(e, ArrayLit):
            et = e.ty[1]
            m = self.m(et)
            if not e.elems:
                return f"A_{m}_new(0)"
            elems = ", ".join(self.expr(x) for x in e.elems)
            return f"A_{m}_lit({len(e.elems)}, ({self.c(et)}[]){{{elems}}})"
        if isinstance(e, Call):
            return self.call(e)
        if isinstance(e, Variant):
            return self.variant(e)
        if isinstance(e, Try):
            return self.try_(e)
        raise AssertionError(type(e))

    def variant(self, e: Variant) -> str:
        t = self.T(e.ty)
        ct = ctype(t)
        tag = next(i for i, (n, _) in enumerate(self.chk.variants(t)) if n == e.name)
        if not e.args:
            return f"(({ct}){{.tag = {tag}}})"
        vals = [self.expr(a) for a in e.args]
        if self.ordered(e.args):
            temps = [self.fresh("v") for _ in vals]
            decls = " ".join(f"{self.c(a.ty)} {tn} = {v};" for a, tn, v in zip(e.args, temps, vals))
            vals, pre = temps, decls + " "
        else:
            pre = None
        payload = ", ".join(f"._{i} = {v}" for i, v in enumerate(vals))
        lit = f"(({ct}){{.tag = {tag}, .u_{e.name} = {{{payload}}}}})"
        return f"({{ {pre}{lit}; }})" if pre else lit

    def try_(self, e: Try) -> str:
        t = self.T(e.operand.ty)
        assert self.fn is not None
        rt = ctype(self.T(self.fn.ret))
        tv = self.fresh("q")
        if t[0] == "opt":
            fail = f"(({rt}){{.tag = 1}})"
            ok = f"{tv}.u_Some._0"
        else:
            fail = f"(({rt}){{.tag = 1, .u_Err = {{._0 = {tv}.u_Err._0}}}})"
            ok = f"{tv}.u_Ok._0"
        return f"({{ {ctype(t)} {tv} = {self.expr(e.operand)}; if ({tv}.tag != 0) {self.ret_code(fail)} {ok}; }})"

    def binary(self, e: Binary) -> str:
        op = e.op
        if op in ("and", "or"):
            c = "&&" if op == "and" else "||"
            return f"({self.expr(e.left)} {c} {self.expr(e.right)})"
        t = e.left.ty
        if self.ordered([e.left, e.right]):
            lt, rt = self.fresh("l"), self.fresh("r")
            inner = Binary(e.line, e.col, op, _Raw(e.line, e.col, lt, t), _Raw(e.line, e.col, rt, t))
            inner.ty = e.ty
            return (f"({{ {self.c(t)} {lt} = {self.expr(e.left)}; {self.c(t)} {rt} = {self.expr(e.right)}; "
                    f"{self.binary(inner)}; }})")
        l, r = self.expr(e.left), self.expr(e.right)
        if op in CMP:
            if t == "str":
                return f"(strcmp({l}, {r}) {op} 0)"
            if isinstance(t, tuple):
                return f"({'' if op == '==' else '!'}eq_{self.m(t)}({l}, {r}))"
            return f"({l} {op} {r})"
        if t == "i64" and self.checked:
            return f"{ARITH_FN[op]}({l}, {r}, {e.line}, {e.col})"
        return f"({l} {op} {r})"

    def call(self, e: Call) -> str:
        name = e.name
        args = e.args
        L = f"{e.line}, {e.col}"
        if name == "print":
            # evaluate every argument first, then write: a failure prints nothing
            decls, parts = [], []
            for i, a in enumerate(args):
                tn = self.fresh("p")
                decls.append(f"{self.c(a.expr.ty)} {tn} = {self.expr(a.expr)};")
                if i:
                    parts.append("aim_putc(' ');")
                parts.append(f"aim_print_{a.expr.ty}({tn});")
            parts.append("aim_putc('\\n');")
            return "({ " + " ".join(decls + parts) + " })"
        if name == "assert":
            a = args[0].expr
            return (f"((void)(({self.expr(a)}) || (aim_fail(\"assert\", \"assertion failed\", {L}, "
                    f"{c_str(show(a))}, 0, 0), 0)))")
        if name == "len":
            return f"(({self.expr(args[0].expr)})->len)"
        if name == "push":
            at = args[0].expr.ty
            return f"A_{self.m(at[1])}_push({self.expr(args[0].expr)}, {self.expr(args[1].expr)})"
        if name == "pop":
            at = args[0].expr.ty
            return f"A_{self.m(at[1])}_pop({self.expr(args[0].expr)}, {L})"
        if name == "fill":
            et = e.ty[1]
            return f"A_{self.m(et)}_fill({self.expr(args[0].expr)}, {self.expr(args[1].expr)}, {L})"
        if name == "copy":
            return self.copy_of(self.expr(args[0].expr), e.ty)
        if name == "sqrt":
            return f"sqrt({self.expr(args[0].expr)})"
        if name == "abs":
            x = self.expr(args[0].expr)
            if e.ty == "f64":
                return f"fabs({x})"
            return f"aim_absi({x}, {L})" if self.checked else f"llabs({x})"
        if name in ("min", "max"):
            suf = "i" if e.ty == "i64" else "f"
            return f"aim_{name}{suf}({self.expr(args[0].expr)}, {self.expr(args[1].expr)})"
        if name == "f64":
            return f"((double)({self.expr(args[0].expr)}))"
        if name == "i64":
            x = self.expr(args[0].expr)
            if args[0].expr.ty == "i64":
                return x
            return f"aim_f2i({x}, {L})" if self.checked else f"((int64_t)({x}))"
        if name == "arg":
            return f"aim_arg({self.expr(args[0].expr)}, {L})"
        if name == "clock":
            return "aim_clock()"
        fn = self.chk.fns[name]
        callee_sub: dict[str, Type] = {}
        cname = f"f_{name}"
        if fn.tparams:
            targs = [self.T(t) for t in e.targs]
            callee_sub = dict(zip(fn.tparams, targs))
            cname = self.instance(fn, targs)
        cargs = []
        for a in args:
            x = self.expr(a.expr)
            cargs.append(f"&({x})" if a.mut else x)
        if self.ordered([a.expr for a in args]):
            temps, decls = [], []
            for a, p, x in zip(args, fn.params, cargs):
                tn = self.fresh("a")
                decls.append(f"{ctype(subst(p.ty, callee_sub))}{'*' if p.mut else ''} {tn} = {x};")
                temps.append(tn)
            return f"({{ {' '.join(decls)} {cname}({', '.join(temps)}); }})"
        return f"{cname}({', '.join(cargs)})"


class _Raw(Expr):
    """Already-generated C expression (used for hoisted temporaries)."""

    def __init__(self, line: int, col: int, code: str, ty: Type):
        super().__init__(line, col)
        self.cname = code
        self.ty = ty
        self.name = code


def generate(prog: Program, chk: Checker, mode: str = "run", checked: bool = True) -> str:
    return Gen(prog, chk, checked).program(mode)
