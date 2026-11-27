"""Type checker and safety rules.

Annotates every Expr with .ty and collects diagnostics (does not stop at the first).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from .errors import CompileError, Diag
from .nodes import (
    ArrayLit, Assign, Binary, Block, Bool, Break, Call, Continue, EnumDef, Expr, ExprStmt,
    Field, Float, FnDef, For, If, Index, Int, Let, Match, Name, Program, Ret, Stmt, Str,
    StructDef, StructLit, TestDef, Try, Type, Unary, Variant, While, has_tp, subst, type_str,
)
from .parser import show

MAX_DEPTH = 3
PRINTABLE = {"i64", "f64", "bool", "str"}
NUMERIC = {"i64", "f64"}
BUILTINS = {
    "print", "len", "push", "pop", "fill", "copy", "sqrt", "abs", "min", "max",
    "f64", "i64", "arg", "clock", "assert",
}
IO_BUILTINS = {"print", "arg", "clock"}
BUILTIN_VARIANTS = {"Some", "None", "Ok", "Err"}
RESERVED_TYPES = {"Option", "Result", "i64", "f64", "bool", "str"}


@dataclass
class Var:
    name: str
    ty: Type
    mut: bool
    line: int
    col: int
    by_ref: bool = False  # mut parameter: accessed through a pointer
    used: bool = False
    mutated: bool = False
    kind: str = "variable"
    cname: str = ""

    def __post_init__(self):
        if not self.cname:
            self.cname = f"(*v_{self.name})" if self.by_ref else f"v_{self.name}"


@dataclass
class FnCtx:
    name: str
    ret: Type
    effects: set[str]
    is_test: bool = False
    tparams: tuple[str, ...] = ()
    uses_io: bool = False
    in_arm: bool = False
    loop_depth: int = 0
    scopes: list[dict[str, Var]] = field(default_factory=list)


def is_place(e: Expr) -> bool:
    if isinstance(e, Name):
        return True
    if isinstance(e, (Field, Index)):
        return is_place(e.base)
    return False


def root_name(e: Expr) -> str | None:
    while isinstance(e, (Field, Index)):
        e = e.base
    return e.name if isinstance(e, Name) else None


class Checker:
    def __init__(self, prog: Program):
        self.prog = prog
        self.diags: list[Diag] = []
        self.structs: dict[str, StructDef] = {}
        self.enums: dict[str, EnumDef] = {}
        self.ret_moved: set[str] | None = None  # locals moved by the 'ret' being checked
        self.fns: dict[str, FnDef] = {}
        self.ctx: FnCtx | None = None
        self.arr_types: set[Type] = set()
        self._heavy_cache: dict[Type, bool] = {}

    # ---------- diagnostics ----------

    def error(self, code: str, msg: str, node, hint: str | None = None):
        self.diags.append(Diag(code, msg, node.line, node.col, hint))

    def warn(self, code: str, msg: str, node, hint: str | None = None):
        self.diags.append(Diag(code, msg, node.line, node.col, hint, severity="warning"))

    @staticmethod
    def suggest(name: str, candidates) -> str | None:
        m = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
        return f"did you mean '{m[0]}'?" if m else None

    # ---------- types ----------

    def resolve(self, t: Type) -> Type:
        """Parser types name every user type ("struct", N); turn enum names into ("enum", N)."""
        if isinstance(t, tuple):
            if t[0] in ("arr", "opt", "res"):
                return (t[0], self.resolve(t[1]))
            if t[0] == "struct" and t[1] in self.enums:
                return ("enum", t[1])
        return t

    def check_type(self, t: Type, node) -> bool:
        if isinstance(t, tuple):
            if t[0] in ("arr", "opt", "res"):
                ok = self.check_type(t[1], node)
                if ok and t[0] == "arr":
                    self.arr_types.add(t)
                return ok
            if t[0] in ("enum", "tp"):
                return True
            if t[1] not in self.structs:
                hint = self.suggest(t[1], list(self.structs) + list(self.enums) + ["i64", "f64", "bool", "str"])
                if t[1] in ("Option", "Result"):
                    hint = f"write {t[1]}[T]"
                elif t[1] in ("int", "float", "string", "String", "usize", "i32"):
                    hint = {"int": "i64", "i32": "i64", "usize": "i64", "float": "f64"}.get(t[1], "str")
                    hint = f"use {hint}"
                elif self.ctx is None and len(t[1]) == 1:
                    hint = "declare type parameters on the fn: fn name[T](...)"
                self.error("E101", f"unknown type '{t[1]}'", node, hint)
                return False
        return True

    def variants(self, t: Type) -> list[tuple[str, list[Type]]] | None:
        """Variants of an enum-like type, in tag order."""
        if isinstance(t, tuple):
            if t[0] == "enum":
                return [(n, ps) for n, ps, _, _ in self.enums[t[1]].variants]
            if t[0] == "opt":
                return [("Some", [t[1]]), ("None", [])]
            if t[0] == "res":
                return [("Ok", [t[1]]), ("Err", ["str"])]
        return None

    def components(self, t: Type) -> list[Type]:
        """Types stored by value inside t."""
        if isinstance(t, tuple):
            if t[0] == "struct" and t[1] in self.structs:
                return [ft for _, ft, _, _ in self.structs[t[1]].fields]
            vs = self.variants(t)
            if vs is not None:
                return [p for _, ps in vs for p in ps]
        return []

    def heavy(self, t: Type) -> bool:
        """True if the type owns a heap array (copying it is not free). Type parameters count as heavy."""
        if t in self._heavy_cache:
            return self._heavy_cache[t]
        r = False
        if isinstance(t, tuple):
            if t[0] in ("arr", "tp"):
                r = True
            else:
                self._heavy_cache[t] = False  # guard recursion
                r = any(self.heavy(ft) for ft in self.components(t))
        self._heavy_cache[t] = r
        return r

    def has_array(self, t: Type, seen: frozenset = frozenset()) -> bool:
        """True if t holds an array type directly (not only via a type parameter)."""
        if not isinstance(t, tuple) or t in seen or t[0] == "tp":
            return False
        return t[0] == "arr" or any(self.has_array(c, seen | {t}) for c in self.components(t))

    def comparable(self, t: Type) -> bool:
        """'==' works on primitives and on structs/enums/Option/Result built from comparable types."""
        if t in PRINTABLE:
            return True
        if isinstance(t, tuple) and t[0] not in ("arr", "tp"):
            return all(self.comparable(c) for c in self.components(t))
        return False

    def note_type(self, t: Type):
        if isinstance(t, tuple) and t[0] == "arr":
            self.arr_types.add(t)
            self.note_type(t[1])

    # ---------- program ----------

    def run(self) -> Program:
        p = self.prog
        for sd in p.structs:
            if sd.name in self.structs:
                self.error("E102", f"struct '{sd.name}' is defined twice", sd)
            if not sd.name[:1].isupper():
                self.error("E103", f"struct name '{sd.name}' must start with an uppercase letter", sd)
            if sd.name in RESERVED_TYPES:
                self.error("E102", f"'{sd.name}' is a builtin type name", sd)
            self.structs[sd.name] = sd
        for ed in p.enums:
            if ed.name in self.structs or ed.name in self.enums or ed.name in RESERVED_TYPES:
                self.error("E102", f"type '{ed.name}' is defined twice", ed)
            if not ed.name[:1].isupper():
                self.error("E103", f"enum name '{ed.name}' must start with an uppercase letter", ed)
            self.enums[ed.name] = ed
        for sd in p.structs:
            sd.fields = [(f, self.resolve(ft), l, c) for f, ft, l, c in sd.fields]
        for ed in p.enums:
            ed.variants = [(v, [self.resolve(t) for t in ps], l, c) for v, ps, l, c in ed.variants]
        for fn in p.fns:
            for prm in fn.params:
                prm.ty = self.resolve(prm.ty)
            fn.ret = self.resolve(fn.ret)
        for sd in p.structs:
            seen = set()
            for fname, ft, l, c in sd.fields:
                node = _Pos(l, c)
                if fname in seen:
                    self.error("E104", f"field '{fname}' appears twice in struct '{sd.name}'", node)
                seen.add(fname)
                self.check_type(ft, node)
        for ed in p.enums:
            seen = set()
            if not ed.variants:
                self.error("E111", f"enum '{ed.name}' has no variants", ed)
            for vname, ps, l, c in ed.variants:
                node = _Pos(l, c)
                if vname in seen:
                    self.error("E104", f"variant '{vname}' appears twice in enum '{ed.name}'", node)
                if not vname[:1].isupper():
                    self.error("E103", f"variant name '{vname}' must start with an uppercase letter", node)
                seen.add(vname)
                for t in ps:
                    self.check_type(t, node)
        self.check_struct_cycles()
        for fn in p.fns:
            if fn.name in BUILTINS or fn.name in BUILTIN_VARIANTS:
                self.error("E105", f"'{fn.name}' is a builtin and cannot be redefined", fn)
            elif fn.name in self.fns:
                self.error("E106", f"function '{fn.name}' is defined twice", fn)
            self.fns[fn.name] = fn
            seen_tp: set[str] = set()
            for tp in fn.tparams:
                if tp in seen_tp or tp in self.structs or tp in self.enums or tp in RESERVED_TYPES:
                    self.error("E112", f"type parameter '{tp}' of fn '{fn.name}' clashes with another type name",
                               fn, "choose another name, e.g. T or U")
                elif not tp[:1].isupper():
                    self.error("E112", f"type parameter '{tp}' must start with an uppercase letter", fn)
                seen_tp.add(tp)
            for prm in fn.params:
                self.check_type(prm.ty, prm)
            if fn.ret != "unit":
                self.check_type(fn.ret, fn)
            for eff in fn.effects:
                if eff != "io":
                    self.error("E107", f"unknown effect '{eff}'", fn, "the only effect is 'io'")
        if "main" in self.fns:
            m = self.fns["main"]
            if m.params or m.ret != "unit":
                self.error("E108", "main must be 'fn main()' with no parameters and no return type", m)
        names = set()
        for t in p.tests:
            if t.name in names:
                self.error("E109", f"test '{t.name}' is defined twice", t)
            names.add(t.name)
        for fn in p.fns:
            self.check_fn(fn)
        for t in p.tests:
            self.check_test(t)
        errors = [d for d in self.diags if d.severity == "error"]
        if errors:
            raise CompileError(self.diags)
        return p

    def check_struct_cycles(self):
        """Structs and enums are stored by value, so they cannot contain themselves."""
        state: dict[str, int] = {}

        def named(t: Type) -> list[str]:
            if isinstance(t, tuple):
                if t[0] in ("opt", "res"):
                    return named(t[1])
                if t[0] in ("struct", "enum") and (t[1] in self.structs or t[1] in self.enums):
                    return [t[1]]
            return []

        def members(name: str):
            if name in self.structs:
                return [(ft, l, c) for _, ft, l, c in self.structs[name].fields]
            return [(t, l, c) for _, ps, l, c in self.enums[name].variants for t in ps]

        def visit(name: str):
            state[name] = 1
            for ft, l, c in members(name):
                for dep in named(ft):
                    s = state.get(dep, 0)
                    if s == 1:
                        self.error("E110", f"type '{name}' contains itself through '{dep}'",
                                   _Pos(l, c), "use an array [T] to hold recursive data")
                    elif s == 0:
                        visit(dep)
            state[name] = 2

        for name in list(self.structs) + list(self.enums):
            if state.get(name, 0) == 0:
                visit(name)

    # ---------- scopes ----------

    def push_scope(self):
        assert self.ctx
        self.ctx.scopes.append({})

    def pop_scope(self):
        assert self.ctx
        for v in self.ctx.scopes.pop().values():
            if v.name == "_":
                continue
            if not v.used and v.kind != "loop variable":
                self.warn("W201", f"{v.kind} '{v.name}' is never used", v,
                          "remove it, or name it '_' (let _ = ...)")
            elif v.mut and not v.mutated and v.kind == "variable":
                self.warn("W202", f"variable '{v.name}' is declared mut but never changed", v,
                          "drop 'mut'")

    def lookup(self, name: str) -> Var | None:
        assert self.ctx
        for s in reversed(self.ctx.scopes):
            if name in s:
                return s[name]
        return None

    def declare(self, v: Var):
        assert self.ctx
        if v.name == "_":
            return
        prev = self.lookup(v.name)
        if prev:
            self.error("E201", f"'{v.name}' is already defined at line {prev.line} (shadowing is not allowed)",
                       v, "choose a different name")
            return
        if v.name in self.fns or v.name in BUILTINS:
            self.error("E202", f"'{v.name}' is a function name and cannot be used as a {v.kind}", v)
            return
        if v.name[:1].isupper():
            self.error("E204", f"{v.kind} name '{v.name}' must start with a lowercase letter "
                       "(uppercase names are types)", v, f"rename it to '{v.name[0].lower() + v.name[1:]}'")
        self.ctx.scopes[-1][v.name] = v

    # ---------- functions ----------

    def check_fn(self, fn: FnDef):
        self.ctx = FnCtx(fn.name, fn.ret, set(fn.effects), tparams=tuple(fn.tparams))
        self.push_scope()
        for prm in fn.params:
            self.note_type(prm.ty)
            self.declare(Var(prm.name, prm.ty, prm.mut, prm.line, prm.col, by_ref=prm.mut, kind="parameter"))
        for r in fn.requires:
            self.expect_bool(self.expr(r), r, "requires")
        if fn.ensures:
            self.push_scope()
            if fn.ret != "unit":
                self.ctx.scopes[-1]["result"] = Var("result", fn.ret, False, fn.line, fn.col, used=True, cname="__result")
            for e in fn.ensures:
                self.expect_bool(self.expr(e), e, "ensures")
            self.ctx.scopes.pop()
        self.block(fn.body, depth=0, new_scope=False)
        if fn.ret != "unit" and not self.terminates(fn.body):
            self.error("E301", f"fn '{fn.name}' must return {type_str(fn.ret)} on every path",
                       _Pos(fn.line, fn.col), "add 'ret <value>' at the end of the body")
        if "io" in self.ctx.effects and not self.ctx.uses_io:
            self.warn("W203", f"fn '{fn.name}' declares '! io' but performs no io", fn, "remove '! io'")
        self.pop_scope()
        self.ctx = None

    def check_test(self, t: TestDef):
        self.ctx = FnCtx(t.name, "unit", {"io"}, is_test=True)
        self.push_scope()
        self.block(t.body, depth=0, new_scope=False)
        self.pop_scope()
        self.ctx = None

    def terminates(self, b: Block) -> bool:
        if not b.stmts:
            return False
        last = b.stmts[-1]
        if isinstance(last, Ret):
            return True
        if isinstance(last, If):
            return last.els is not None and self.terminates(last.then) and self.terminates(last.els)
        if isinstance(last, While):
            return isinstance(last.cond, Bool) and last.cond.value and not self.has_break(last.body)
        if isinstance(last, Match):
            return bool(last.arms) and all(self.terminates(a.body) for a in last.arms)
        if isinstance(last, ExprStmt) and isinstance(last.expr, Call) and last.expr.name == "assert":
            a = last.expr.args
            return len(a) == 1 and isinstance(a[0].expr, Bool) and not a[0].expr.value
        return False

    def has_break(self, b: Block) -> bool:
        for s in b.stmts:
            if isinstance(s, Break):
                return True
            if isinstance(s, If) and (self.has_break(s.then) or (s.els and self.has_break(s.els))):
                return True
            if isinstance(s, Match) and any(self.has_break(a.body) for a in s.arms):
                return True
        return False

    # ---------- statements ----------

    def block(self, b: Block, depth: int, new_scope: bool = True):
        if depth > MAX_DEPTH:
            self.error("E302", f"blocks are nested {depth} levels deep (max {MAX_DEPTH})", _Pos(b.line, 1),
                       "move the inner part into its own fn")
        if new_scope:
            self.push_scope()
        done = False
        for s in b.stmts:
            if done:
                self.warn("W204", "unreachable statement", s, "remove code after ret/break/continue")
                done = False
            self.stmt(s, depth)
            if isinstance(s, (Ret, Break, Continue)):
                done = True
        if new_scope:
            self.pop_scope()

    def stmt(self, s: Stmt, depth: int):
        ctx = self.ctx
        assert ctx
        if isinstance(s, Let):
            if s.ann is not None:
                s.ann = self.resolve(s.ann)
            t = self.expr(s.value, expect=s.ann)
            if s.ann is not None:
                if self.check_type(s.ann, s):
                    self.note_type(s.ann)
                    self.expect_type(t, s.ann, s.value, f"initializer of '{s.name}'")
                t = s.ann
            if t == "unit":
                self.error("E203", f"'{show(s.value)}' produces no value", s.value)
            if s.name == "_" and isinstance(t, tuple) and t[0] == "res":
                self.error("E711", f"discarding the Result of '{show(s.value)}' hides its error", s.value,
                           "handle it: use ? or match on Ok/Err")
            self.value_use(s.value)
            self.declare(Var(s.name, t, s.mut, s.line, s.col))
        elif isinstance(s, Assign):
            self.assign(s)
        elif isinstance(s, If):
            self.expect_bool(self.expr(s.cond), s.cond, "if condition")
            self.block(s.then, depth + 1)
            if s.els is not None:
                if getattr(s.els, "is_elif", False):
                    self.stmt(s.els.stmts[0], depth)
                else:
                    self.block(s.els, depth + 1)
        elif isinstance(s, While):
            self.expect_bool(self.expr(s.cond), s.cond, "while condition")
            ctx.loop_depth += 1
            self.block(s.body, depth + 1)
            ctx.loop_depth -= 1
        elif isinstance(s, For):
            for e in (s.start, s.stop):
                self.expect_type(self.expr(e), "i64", e, "range bound")
            ctx.loop_depth += 1
            self.push_scope()
            self.declare(Var(s.var, "i64", False, s.line, s.col, kind="loop variable"))
            self.block(s.body, depth + 1, new_scope=False)
            self.pop_scope()
            ctx.loop_depth -= 1
        elif isinstance(s, Ret):
            if ctx.is_test:
                self.error("E303", "'ret' is not allowed in a test", s)
                return
            if s.value is None:
                if ctx.ret != "unit":
                    self.error("E304", f"'ret' needs a value of type {type_str(ctx.ret)}", s)
            else:
                if ctx.ret == "unit":
                    self.error("E305", f"fn '{ctx.name}' has no return type but 'ret' has a value", s,
                               f"add '-> T' to fn '{ctx.name}', or write plain 'ret'")
                    self.expr(s.value)
                    return
                # locals die at 'ret', so storing one in the returned value moves it
                self.ret_moved = set()
                t = self.expr(s.value, expect=ctx.ret)
                self.expect_type(t, ctx.ret, s.value, "return value")
                self.value_use(s.value)
                self.ret_moved = None
        elif isinstance(s, Match):
            self.match(s, depth)
        elif isinstance(s, (Break, Continue)):
            if ctx.loop_depth == 0:
                self.error("E306", f"'{'break' if isinstance(s, Break) else 'continue'}' outside a loop", s)
        elif isinstance(s, ExprStmt):
            t = self.expr(s.expr)
            if ctx.is_test and t == "bool":
                s.is_assert = True
            elif t is None:
                pass
            elif isinstance(t, tuple) and t[0] == "res":
                self.error("E711", f"the Result of '{show(s.expr)}' is not handled", s.expr,
                           "use ? to pass the error up, or match on Ok/Err")
            elif t != "unit":
                hint = "bind it: let _ = ..." if isinstance(s.expr, Call) else None
                if ctx.is_test:
                    hint = "a test line must be a bool assertion (e.g. f(1) == 2) or a call"
                elif ctx.in_arm:
                    hint = "match is a statement, not an expression: write '=> ret value' or assign a variable"
                self.error("E307", f"value of type {type_str(t)} is not used", s.expr, hint)
            elif not isinstance(s.expr, Call):
                self.error("E307", "expression statement has no effect", s.expr)

    def match(self, s: Match, depth: int):
        ctx = self.ctx
        assert ctx
        t = self.expr(s.subject)
        vs = self.variants(t) if t is not None else None
        if t is not None and vs is None:
            hint = "use if / else if for values" if t in PRINTABLE else None
            self.error("E707", f"cannot match on {type_str(t)}; match needs an enum, Option or Result",
                       s.subject, hint)
        enum = t[1] if isinstance(t, tuple) and t[0] == "enum" else None
        tags = {n: (i, ps) for i, (n, ps) in enumerate(vs or [])}
        seen: set[str] = set()
        wild = False
        for arm in s.arms:
            arm.tag, arm.ptys = None, []
            if wild:
                self.error("E708", "unreachable match arm after '_'", arm, "remove it or move '_' last")
            if arm.variant is None:
                if vs is not None and len(seen) == len(vs):
                    self.error("E708", "'_' matches nothing: every variant is already covered", arm, "remove the '_' arm")
                wild = True
            elif vs is not None:
                want = f"{enum}.{arm.variant}" if enum else arm.variant
                got = f"{arm.enum}.{arm.variant}" if arm.enum else arm.variant
                if arm.variant not in tags or arm.enum != enum:
                    names = [f"{enum}.{n}" if enum else n for n in tags]
                    self.error("E703", f"'{got}' is not a variant of {type_str(t)}", arm,
                               self.suggest(want, names) or "variants: " + ", ".join(names))
                elif arm.variant in seen:
                    self.error("E709", f"'{got}' is matched twice", arm, "merge the two arms")
                else:
                    seen.add(arm.variant)
                    arm.tag, arm.ptys = tags[arm.variant]
                    if len(arm.binds) != len(arm.ptys):
                        self.error("E704", f"'{got}' has {len(arm.ptys)} payload value(s), pattern binds {len(arm.binds)}",
                                   arm, "write " + got + ("(" + ", ".join("_" for _ in arm.ptys) + ")" if arm.ptys else ""))
            self.push_scope()
            for (bname, l, c), bt in zip(arm.binds, arm.ptys or [None] * len(arm.binds)):
                self.declare(Var(bname, bt, False, l, c, kind="binding"))
            saved, ctx.in_arm = ctx.in_arm, True
            self.block(arm.body, depth + 1, new_scope=False)
            ctx.in_arm = saved
            self.pop_scope()
        if vs is not None and not wild:
            missing = [f"{enum}.{n}" if enum else n for n in tags if n not in seen]
            if missing:
                self.error("E710", f"match is not exhaustive: missing {', '.join(missing)}", s,
                           "add an arm for each, or '_ => ...' last")

    def assign(self, s: Assign):
        if not is_place(s.target):
            self.error("E401", f"cannot assign to '{show(s.target)}'", s.target)
            self.expr(s.value)
            return
        tt = self.expr(s.target)
        rn = root_name(s.target)
        v = self.lookup(rn) if rn else None
        if v is not None:
            if not v.mut:
                hint = (f"declare it with 'let mut {v.name}'" if v.kind == "variable"
                        else f"declare the parameter as 'mut {v.name}'" if v.kind == "parameter" else None)
                self.error("E402", f"cannot modify immutable {v.kind} '{v.name}'", s.target, hint)
            v.mutated = True
        vt = self.expr(s.value, expect=tt)
        if s.op == "=":
            self.expect_type(vt, tt, s.value, f"assignment to '{show(s.target)}'")
            self.value_use(s.value)
        else:
            if tt not in NUMERIC:
                self.error("E403", f"'{s.op}' needs i64 or f64, '{show(s.target)}' is {type_str(tt)}", s.target)
            elif s.op == "%=" and tt != "i64":
                self.error("E403", "'%=' needs i64", s.target)
            else:
                self.expect_type(vt, tt, s.value, f"'{s.op}' operand")

    def value_use(self, e: Expr):
        """A value is being stored somewhere: forbid silent aliasing of heap data."""
        if isinstance(e, Try):
            e = e.operand
        if self.ret_moved is not None and isinstance(e, Name):
            v = self.lookup(e.name)
            if v is not None and v.kind == "variable" and e.name not in self.ret_moved:
                self.ret_moved.add(e.name)
                return
        if e.ty is not None and is_place(e) and self.heavy(e.ty):
            if self.has_array(e.ty):
                msg = f"storing '{show(e)}' would share its array storage"
            else:  # heavy only through a type parameter
                msg = (f"storing '{show(e)}' ({type_str(e.ty)}) may share array storage: "
                       f"a type parameter can be an array, so it needs copy() like one")
            self.error("E404", msg, e, f"write copy({show(e)}) to make an independent copy")

    # ---------- expressions ----------

    def expect_type(self, got: Type, want: Type, node, what: str):
        if got is None or want is None or got == want:
            return
        hint = None
        if got == "i64" and want == "f64":
            hint = f"convert with f64({show(node)})" if isinstance(node, Expr) else None
            if isinstance(node, Int):
                hint = f"write {node.value}.0"
        elif got == "f64" and want == "i64":
            hint = f"convert with i64({show(node)}) (truncates)" if isinstance(node, Expr) else None
        self.error("E501", f"{what}: expected {type_str(want)}, found {type_str(got)}", node, hint)

    def expect_bool(self, t: Type, node, what: str):
        self.expect_type(t, "bool", node, what)

    def expr(self, e: Expr, expect: Type | None = None) -> Type:
        t = self._expr(e, expect)
        e.ty = t
        return t

    def _expr(self, e: Expr, expect: Type | None) -> Type:
        ctx = self.ctx
        assert ctx
        if isinstance(e, Int):
            if e.value > 2**63 - 1:
                self.error("E502", "integer literal does not fit in i64", e)
            return "i64"
        if isinstance(e, Float):
            return "f64"
        if isinstance(e, Bool):
            return "bool"
        if isinstance(e, Str):
            return "str"
        if isinstance(e, Name):
            v = self.lookup(e.name)
            if v is None:
                if e.name in self.fns or e.name in BUILTINS:
                    self.error("E503", f"'{e.name}' is a function; call it with ()", e)
                else:
                    names = [n for s in ctx.scopes for n in s]
                    self.error("E504", f"unknown variable '{e.name}'", e, self.suggest(e.name, names))
                return None
            v.used = True
            e.cname = v.cname
            return v.ty
        if isinstance(e, Unary):
            t = self.expr(e.operand)
            if e.op == "not":
                self.expect_bool(t, e.operand, "operand of 'not'")
                return "bool"
            if t is not None and t not in NUMERIC:
                self.error("E505", f"cannot negate {type_str(t)}", e)
            return t
        if isinstance(e, Binary):
            return self.binary(e)
        if isinstance(e, Call):
            return self.call(e, expect)
        if isinstance(e, Index):
            bt = self.expr(e.base)
            it = self.expr(e.index)
            self.expect_type(it, "i64", e.index, "array index")
            if bt is None:
                return None
            if not (isinstance(bt, tuple) and bt[0] == "arr"):
                self.error("E506", f"cannot index into {type_str(bt)}", e.base)
                return None
            return bt[1]
        if isinstance(e, Field):
            bt = self.expr(e.base)
            if bt is None:
                return None
            if not (isinstance(bt, tuple) and bt[0] == "struct"):
                hint = "use len(x) for the length of an array" if e.name in ("len", "length") else None
                self.error("E507", f"{type_str(bt)} has no fields", e, hint)
                return None
            sd = self.structs[bt[1]]
            for fname, ft, _, _ in sd.fields:
                if fname == e.name:
                    return ft
            self.error("E508", f"struct '{sd.name}' has no field '{e.name}'", e,
                       self.suggest(e.name, [f for f, _, _, _ in sd.fields]))
            return None
        if isinstance(e, StructLit):
            sd = self.structs.get(e.name)
            if sd is None:
                self.error("E509", f"unknown struct '{e.name}'", e, self.suggest(e.name, self.structs))
                for _, v, _, _ in e.fields:
                    self.expr(v)
                return None
            want = {f: ft for f, ft, _, _ in sd.fields}
            given = set()
            for fname, v, l, c in e.fields:
                node = _Pos(l, c)
                if fname in given:
                    self.error("E510", f"field '{fname}' given twice", node)
                given.add(fname)
                if fname not in want:
                    self.error("E508", f"struct '{sd.name}' has no field '{fname}'", node,
                               self.suggest(fname, want))
                    self.expr(v)
                    continue
                vt = self.expr(v, expect=want[fname])
                self.expect_type(vt, want[fname], v, f"field '{fname}'")
                self.value_use(v)
            missing = [f for f in want if f not in given]
            if missing:
                self.error("E511", f"struct literal '{sd.name}' is missing field(s): {', '.join(missing)}", e)
            return ("struct", e.name)
        if isinstance(e, Variant):
            return self.variant(e, expect)
        if isinstance(e, Try):
            return self.try_(e, expect)
        if isinstance(e, ArrayLit):
            et = expect[1] if isinstance(expect, tuple) and expect[0] == "arr" else None
            if not e.elems:
                if et is None:
                    self.error("E512", "cannot infer the type of an empty array", e,
                               "annotate it: let xs: [i64] = []")
                    return None
                self.note_type(expect)
                return expect
            for el in e.elems:
                t = self.expr(el, expect=et)
                if et is None:
                    et = t
                else:
                    self.expect_type(t, et, el, "array element")
                self.value_use(el)
            if et is None:
                return None
            at = ("arr", et)
            self.note_type(at)
            return at
        raise AssertionError(type(e))

    def variant(self, e: Variant, expect: Type | None) -> Type:
        args = e.args or []
        if e.enum is None:  # Some / None / Ok / Err
            kind = "opt" if e.name in ("Some", "None") else "res"
            exp = expect if isinstance(expect, tuple) and expect[0] == kind else None
            want_args = 0 if e.name == "None" else 1
            if e.args is not None and want_args == 0:
                self.error("E704", "'None' takes no value", e, "write None")
            elif len(args) != want_args:
                self.error("E704", f"'{e.name}' takes one value", e, f"write {e.name}(x)")
            for a in args[want_args:]:
                self.expr(a)
            if e.name in ("Some", "Ok") and args:
                inner = self.expr(args[0], expect=exp[1] if exp else None)
                self.value_use(args[0])
                if exp is not None:
                    self.expect_type(inner, exp[1], args[0], f"value of {e.name}")
                    return exp
                if inner is None or inner == "unit":
                    return None
                return (kind, inner)
            if e.name == "Err" and args:
                self.expect_type(self.expr(args[0], expect="str"), "str", args[0], "Err message")
            if exp is None:
                ty = "Option[i64]" if kind == "opt" else "Result[i64]"
                self.error("E701", f"cannot infer the type of '{show(e)}'", e,
                           f"annotate it: let x: {ty} = {show(e)}")
                return None
            return exp
        ed = self.enums.get(e.enum)
        if ed is None:
            hint = self.suggest(e.enum, self.enums)
            if e.enum in self.structs:
                hint = f"'{e.enum}' is a struct; struct literals use braces: {e.enum}{{field: value}}"
            self.error("E702", f"unknown enum '{e.enum}'", e, hint)
            for a in args:
                self.expr(a)
            return None
        ps = next((ps for n, ps, _, _ in ed.variants if n == e.name), None)
        if ps is None:
            self.error("E703", f"enum '{ed.name}' has no variant '{e.name}'", e,
                       self.suggest(e.name, [n for n, _, _, _ in ed.variants])
                       or "variants: " + ", ".join(f"{ed.name}.{n}" for n, _, _, _ in ed.variants))
            for a in args:
                self.expr(a)
            return None
        if e.args is None and ps:
            self.error("E704", f"'{ed.name}.{e.name}' needs {len(ps)} value(s)", e,
                       f"write {ed.name}.{e.name}({', '.join(type_str(p) for p in ps)})")
        elif e.args is not None and not ps:
            self.error("E704", f"'{ed.name}.{e.name}' has no payload", e, f"write {ed.name}.{e.name} without ()")
        elif e.args is not None and len(args) != len(ps):
            self.error("E704", f"'{ed.name}.{e.name}' takes {len(ps)} value(s), {len(args)} given", e)
        for a, pt in zip(args, ps):
            self.expect_type(self.expr(a, expect=pt), pt, a, f"payload of {ed.name}.{e.name}")
            self.value_use(a)
        for a in args[len(ps):]:
            self.expr(a)
        return ("enum", ed.name)

    def try_(self, e: Try, expect: Type | None) -> Type:
        ctx = self.ctx
        assert ctx
        t = self.expr(e.operand)
        if t is None:
            return None
        if not (isinstance(t, tuple) and t[0] in ("opt", "res")):
            self.error("E705", f"'?' needs an Option or Result, found {type_str(t)}", e)
            return None
        kind = "Option" if t[0] == "opt" else "Result"
        r = ctx.ret
        if ctx.is_test or not (isinstance(r, tuple) and r[0] == t[0]):
            where = "a test" if ctx.is_test else f"fn '{ctx.name}' returns {type_str(r) if r != 'unit' else 'nothing'}"
            self.error("E706", f"'?' on {kind} needs the fn to return {kind}[...], but {where}", e,
                       "match on the value instead" if ctx.is_test else
                       f"change the return type to {kind}[...], or match on the value")
        return t[1]

    def binary(self, e: Binary) -> Type:
        lt = self.expr(e.left)
        rt = self.expr(e.right, expect=lt)
        op = e.op
        if op in ("and", "or"):
            self.expect_bool(lt, e.left, f"left side of '{op}'")
            self.expect_bool(rt, e.right, f"right side of '{op}'")
            return "bool"
        if lt is None or rt is None:
            return "bool" if op in ("==", "!=", "<", "<=", ">", ">=") else None
        if lt != rt:
            hint = None
            if {lt, rt} == {"i64", "f64"}:
                side = e.left if lt == "i64" else e.right
                hint = f"no implicit conversion: wrap the i64 side as f64({show(side)})"
            self.error("E513", f"'{op}' between {type_str(lt)} and {type_str(rt)}", e, hint)
            return "bool" if op in ("==", "!=", "<", "<=", ">", ">=") else None
        if op in ("==", "!="):
            if not self.comparable(lt):
                hint = "compare fields or elements one by one"
                if has_tp(lt):
                    hint = "values of a type parameter cannot be compared"
                self.error("E514", f"cannot compare {type_str(lt)} with '{op}'", e, hint)
            return "bool"
        if op in ("<", "<=", ">", ">="):
            if lt not in NUMERIC:
                self.error("E514", f"cannot order {type_str(lt)} with '{op}'", e)
            return "bool"
        if lt not in NUMERIC:
            hint = "strings cannot be concatenated yet; print parts separately: print(a, b)" if lt == "str" else None
            self.error("E515", f"'{op}' needs i64 or f64, found {type_str(lt)}", e, hint)
            return None
        if op == "%" and lt != "i64":
            self.error("E515", "'%' needs i64", e)
            return None
        return lt

    # ---------- calls ----------

    def call(self, e: Call, expect: Type | None) -> Type:
        ctx = self.ctx
        assert ctx
        if e.name in BUILTINS:
            if e.name in IO_BUILTINS:
                self.need_io(e)
            return self.builtin(e, expect)
        fn = self.fns.get(e.name)
        if fn is None:
            hint = self.suggest(e.name, list(self.fns) + sorted(BUILTINS))
            if e.name in self.structs:
                hint = f"struct literals use braces: {e.name}{{field: value}}"
            self.error("E601", f"unknown function '{e.name}'", e, hint)
            for a in e.args:
                self.expr(a.expr)
            return None
        if "io" in fn.effects:
            self.need_io(e)
        if len(e.args) != len(fn.params):
            self.error("E602", f"'{fn.name}' takes {len(fn.params)} argument(s), {len(e.args)} given", e,
                       f"signature: {sig(fn)}")
        binding: dict[str, Type] = {}
        tps = set(fn.tparams)
        types: list[Type] = []
        for a, p in zip(e.args, fn.params):
            exp = p.ty if not tps else (subst(p.ty, binding) if free_tps(p.ty, tps, binding) == set() else None)
            t = self.expr(a.expr, expect=exp)
            types.append(t)
            if tps:
                unify(p.ty, t, tps, binding)
        if tps and expect is not None:
            unify(fn.ret, expect, tps, binding)
        e.targs = []
        if tps:
            unbound = [tp for tp in fn.tparams if tp not in binding]
            if unbound:
                self.error("E713", f"cannot infer type parameter {', '.join(unbound)} of '{fn.name}'", e,
                           "annotate the result: let x: T = ...")
                return None
            e.targs = [binding[tp] for tp in fn.tparams]
            if not ctx.is_test and fn.name == ctx.name and e.targs != [("tp", tp) for tp in fn.tparams]:
                self.error("E714", f"generic fn '{fn.name}' calls itself with different type arguments "
                           f"({', '.join(type_str(t) for t in e.targs)})", e,
                           "this needs infinitely many instances; recurse with the same types")
        for a, p, t in zip(e.args, fn.params, types):
            self.expect_type(t, subst(p.ty, binding), a.expr, f"argument '{p.name}' of '{fn.name}'")
            if p.mut and not a.mut:
                self.error("E603", f"parameter '{p.name}' of '{fn.name}' is mut; mark the argument", a.expr,
                           f"write {fn.name}(..., mut {show(a.expr)}, ...)")
            elif a.mut and not p.mut:
                self.error("E604", f"parameter '{p.name}' of '{fn.name}' is not mut", a.expr, "remove 'mut'")
            elif a.mut:
                self.mut_arg(a.expr)
        for a in e.args[len(fn.params):]:
            self.expr(a.expr)
        self.check_alias(e)
        return subst(fn.ret, binding)

    def need_io(self, e: Call):
        ctx = self.ctx
        assert ctx
        ctx.uses_io = True
        if "io" not in ctx.effects:
            self.error("E605", f"'{e.name}' performs io but fn '{ctx.name}' is not marked '! io'", e,
                       f"add '! io' after the return type of fn '{ctx.name}'")

    def mut_arg(self, a: Expr):
        if not is_place(a):
            self.error("E606", f"'mut {show(a)}' needs a variable, field or element", a)
            return
        rn = root_name(a)
        v = self.lookup(rn) if rn else None
        if v is None:
            return
        if not v.mut:
            self.error("E607", f"cannot pass immutable {v.kind} '{v.name}' as mut", a,
                       f"declare it with 'let mut {v.name}'" if v.kind == "variable" else None)
        v.mutated = True

    def check_alias(self, e: Call):
        roots: list[tuple[str, bool, Expr]] = []
        for a in e.args:
            if a.expr.ty is None or not is_place(a.expr):
                continue
            if a.mut or self.heavy(a.expr.ty):
                roots.append((root_name(a.expr) or "", a.mut, a.expr))
        for i, (r1, m1, x1) in enumerate(roots):
            for r2, m2, _ in roots[i + 1:]:
                if r1 == r2 and (m1 or m2):
                    self.error("E608", f"'{r1}' is passed as mut and also used in another argument of the same call",
                               x1, "pass a copy() for the read-only argument")

    def builtin(self, e: Call, expect: Type | None) -> Type:
        name, args = e.name, e.args

        def arity(*ns: int) -> bool:
            if len(args) not in ns:
                want = " or ".join(str(n) for n in ns)
                self.error("E602", f"'{name}' takes {want} argument(s), {len(args)} given", e)
                for a in args:
                    self.expr(a.expr)
                return False
            return True

        def no_mut(idx: set[int] = set()):
            for i, a in enumerate(args):
                if a.mut and i not in idx:
                    self.error("E604", f"argument {i + 1} of '{name}' is not mut", a.expr, "remove 'mut'")

        if name == "print":
            no_mut()
            if not args:
                self.error("E602", "'print' needs at least one argument", e)
            for a in args:
                t = self.expr(a.expr)
                if t is not None and t not in PRINTABLE:
                    self.error("E610", f"cannot print {type_str(t)}", a.expr, "print its fields or elements")
            return "unit"
        if name == "assert":
            if not arity(1):
                return "unit"
            no_mut()
            self.expect_bool(self.expr(args[0].expr), args[0].expr, "assert condition")
            return "unit"
        if name == "len":
            if not arity(1):
                return "i64"
            no_mut()
            t = self.expr(args[0].expr)
            if t is not None and not (isinstance(t, tuple) and t[0] == "arr"):
                self.error("E611", f"len() needs an array, found {type_str(t)}", args[0].expr)
            return "i64"
        if name in ("push", "pop"):
            if not arity(2 if name == "push" else 1):
                return None
            at = self.expr(args[0].expr)
            if not args[0].mut:
                self.error("E603", f"first argument of '{name}' must be marked mut", args[0].expr,
                           f"write {name}(mut {show(args[0].expr)}{', ...' if name == 'push' else ''})")
            else:
                self.mut_arg(args[0].expr)
            if at is not None and not (isinstance(at, tuple) and at[0] == "arr"):
                self.error("E611", f"'{name}' needs an array, found {type_str(at)}", args[0].expr)
                at = None
            if name == "pop":
                return at[1] if at else None
            no_mut({0})
            et = at[1] if at else None
            vt = self.expr(args[1].expr, expect=et)
            self.expect_type(vt, et, args[1].expr, "pushed value")
            self.value_use(args[1].expr)
            self.check_alias(e)
            return "unit"
        if name == "fill":
            if not arity(2):
                return None
            no_mut()
            self.expect_type(self.expr(args[0].expr), "i64", args[0].expr, "fill count")
            et = expect[1] if isinstance(expect, tuple) and expect[0] == "arr" else None
            vt = self.expr(args[1].expr, expect=et)
            if vt is None or vt == "unit":
                return None
            at = ("arr", vt)
            self.note_type(at)
            return at
        if name == "copy":
            if not arity(1):
                return None
            no_mut()
            return self.expr(args[0].expr)
        if name in ("sqrt",):
            if not arity(1):
                return "f64"
            no_mut()
            self.expect_type(self.expr(args[0].expr), "f64", args[0].expr, f"argument of {name}")
            return "f64"
        if name == "abs":
            if not arity(1):
                return None
            no_mut()
            t = self.expr(args[0].expr)
            if t is not None and t not in NUMERIC:
                self.error("E612", f"abs() needs i64 or f64, found {type_str(t)}", args[0].expr)
            return t
        if name in ("min", "max"):
            if not arity(2):
                return None
            no_mut()
            t1 = self.expr(args[0].expr)
            t2 = self.expr(args[1].expr, expect=t1)
            if t1 is not None and t1 not in NUMERIC:
                self.error("E612", f"{name}() needs i64 or f64, found {type_str(t1)}", args[0].expr)
                return None
            self.expect_type(t2, t1, args[1].expr, f"second argument of {name}")
            return t1
        if name in ("f64", "i64"):
            if not arity(1):
                return name
            no_mut()
            src = "i64" if name == "f64" else "f64"
            t = self.expr(args[0].expr)
            if t == name:
                self.warn("W205", f"{name}() of a value that is already {name}", e, "remove the conversion")
            else:
                self.expect_type(t, src, args[0].expr, f"argument of {name}()")
            return name
        if name == "arg":
            if not arity(1):
                return "i64"
            no_mut()
            self.expect_type(self.expr(args[0].expr), "i64", args[0].expr, "argument index")
            return "i64"
        if name == "clock":
            arity(0)
            return "f64"
        raise AssertionError(name)


@dataclass
class _Pos:
    line: int
    col: int


def free_tps(t: Type, tps: set[str], binding: dict[str, Type]) -> set[str]:
    if not isinstance(t, tuple):
        return set()
    if t[0] == "tp":
        return {t[1]} if t[1] in tps and t[1] not in binding else set()
    if t[0] in ("arr", "opt", "res"):
        return free_tps(t[1], tps, binding)
    return set()


def unify(pt: Type, at: Type, tps: set[str], binding: dict[str, Type]):
    """Bind the callee's type parameters in pt from the argument type at (first binding wins)."""
    if at is None:
        return
    if isinstance(pt, tuple) and pt[0] == "tp" and pt[1] in tps:
        if pt[1] not in binding and at != "unit":
            binding[pt[1]] = at
        return
    if isinstance(pt, tuple) and isinstance(at, tuple) and pt[0] == at[0] and pt[0] in ("arr", "opt", "res"):
        unify(pt[1], at[1], tps, binding)


def sig(fn: FnDef) -> str:
    ps = ", ".join(("mut " if p.mut else "") + f"{p.name}: {type_str(p.ty)}" for p in fn.params)
    tp = f"[{', '.join(fn.tparams)}]" if fn.tparams else ""
    s = f"fn {fn.name}{tp}({ps})"
    if fn.ret != "unit":
        s += f" -> {type_str(fn.ret)}"
    if fn.effects:
        s += " ! " + ", ".join(fn.effects)
    return s


def check(prog: Program) -> tuple[Program, Checker]:
    c = Checker(prog)
    c.run()
    return prog, c
