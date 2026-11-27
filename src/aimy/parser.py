"""Recursive-descent parser."""

from __future__ import annotations

from .errors import CompileError, Diag
from .lexer import Tok, lex
from .nodes import (
    Arg, Arm, ArrayLit, Assign, Binary, Block, Bool, Break, Call, Continue, EnumDef,
    Expr, ExprStmt, Field, Float, FnDef, For, If, Index, Int, Let, Match, Name, Param,
    Program, Ret, Stmt, Str, StructDef, StructLit, TestDef, Try, Type, Unary, Variant, While,
)

PRIMS = {"i64", "f64", "bool", "str"}
CMP_OPS = {"==", "!=", "<", "<=", ">", ">="}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%="}
INT_MAX = 2**63 - 1
BUILTIN_VARIANTS = {"Some": 1, "None": 0, "Ok": 1, "Err": 1}
GENERIC_TYPES = {"Option": "opt", "Result": "res"}


class Parser:
    def __init__(self, toks: list[Tok]):
        self.toks = toks
        self.i = 0
        self.tparams: list[str] = []
        self.in_arm = False

    # ---------- helpers ----------

    @property
    def tok(self) -> Tok:
        return self.toks[self.i]

    def peek(self, k: int = 1) -> Tok:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def err(self, msg: str, hint: str | None = None, tok: Tok | None = None):
        t = tok or self.tok
        raise CompileError([Diag("E002", msg, t.line, t.col, hint)])

    def at(self, kind: str, value: str | None = None) -> bool:
        t = self.tok
        return t.kind == kind and (value is None or t.value == value)

    def at_op(self, value: str) -> bool:
        return self.at("OP", value)

    def at_kw(self, value: str) -> bool:
        return self.at("KW", value)

    def advance(self) -> Tok:
        t = self.tok
        self.i += 1
        return t

    def expect_op(self, value: str, hint: str | None = None) -> Tok:
        if not self.at_op(value):
            self.err(f"expected '{value}', found {self.describe()}", hint)
        return self.advance()

    def expect_kw(self, value: str, hint: str | None = None) -> Tok:
        if not self.at_kw(value):
            self.err(f"expected '{value}', found {self.describe()}", hint)
        return self.advance()

    def expect_ident(self, what: str = "identifier") -> Tok:
        if not self.at("IDENT"):
            hint = None
            if self.tok.kind == "KW":
                hint = f"'{self.tok.value}' is a reserved word"
            self.err(f"expected {what}, found {self.describe()}", hint)
        return self.advance()

    def describe(self) -> str:
        t = self.tok
        if t.kind == "NL":
            return "end of line"
        if t.kind == "EOF":
            return "end of file"
        return f"'{t.value}'"

    def skip_nl(self):
        while self.at("NL"):
            self.advance()

    def end_stmt(self):
        if self.in_arm and self.at_op(","):
            self.advance()
        if self.at("NL"):
            self.skip_nl()
        elif self.at_op("}"):
            pass
        else:
            self.err(f"expected end of line after statement, found {self.describe()}",
                     "put one statement per line")

    # ---------- top level ----------

    def program(self) -> Program:
        prog = Program()
        self.skip_nl()
        while not self.at("EOF"):
            if self.at_kw("fn"):
                prog.fns.append(self.fn_def())
            elif self.at_kw("struct"):
                prog.structs.append(self.struct_def())
            elif self.at_kw("enum"):
                prog.enums.append(self.enum_def())
            elif self.at_kw("test"):
                prog.tests.append(self.test_def())
            else:
                self.err(f"expected 'fn', 'struct', 'enum' or 'test' at top level, found {self.describe()}")
            self.skip_nl()
        return prog

    def end_label(self, name: str, kind: str):
        if not self.at_kw("end"):
            self.err(f"expected 'end {name}' after closing '}}' of {kind} '{name}'",
                     f"close every top-level definition with '}} end {name}'")
        self.advance()
        t = self.expect_ident("name after 'end'")
        if t.value != name:
            self.err(f"'end {t.value}' does not match {kind} '{name}'",
                     f"write 'end {name}' (braces may be unbalanced above)", t)
        if not (self.at("NL") or self.at("EOF")):
            self.err(f"expected end of line after 'end {name}'")

    def struct_def(self) -> StructDef:
        kw = self.advance()
        name = self.expect_ident("struct name").value
        self.expect_op("{")
        fields: list[tuple[str, Type, int, int]] = []
        self.skip_nl()
        while not self.at_op("}"):
            f = self.expect_ident("field name")
            self.expect_op(":")
            fields.append((f.value, self.type_(), f.line, f.col))
            if self.at_op(","):
                self.advance()
            self.skip_nl()
        self.advance()
        self.end_label(name, "struct")
        return StructDef(name, fields, kw.line, kw.col)

    def enum_def(self) -> EnumDef:
        kw = self.advance()
        name = self.expect_ident("enum name").value
        self.expect_op("{")
        variants: list[tuple[str, list[Type], int, int]] = []
        self.skip_nl()
        while not self.at_op("}"):
            v = self.expect_ident("variant name")
            payload: list[Type] = []
            if self.at_op("("):
                self.advance()
                while not self.at_op(")"):
                    if self.at("IDENT") and self.peek().kind == "OP" and self.peek().value == ":":
                        self.err("variant payloads are positional types, not named fields",
                                 f"write {v.value}(T1, T2); use a struct for named fields")
                    payload.append(self.type_())
                    if not self.at_op(")"):
                        self.expect_op(",")
                self.advance()
            elif self.at_op("{"):
                self.err("variant payloads use parentheses", f"write {v.value}(T1, T2)")
            variants.append((v.value, payload, v.line, v.col))
            if self.at_op(","):
                self.advance()
            elif not (self.at("NL") or self.at_op("}")):
                self.err(f"expected ',' or end of line after variant, found {self.describe()}")
            self.skip_nl()
        self.advance()
        self.end_label(name, "enum")
        return EnumDef(name, variants, kw.line, kw.col)

    def fn_def(self) -> FnDef:
        kw = self.advance()
        name = self.expect_ident("function name").value
        tparams: list[str] = []
        if self.at_op("["):
            self.advance()
            while not self.at_op("]"):
                tparams.append(self.expect_ident("type parameter").value)
                if not self.at_op("]"):
                    self.expect_op(",")
            self.advance()
        elif self.at_op("<"):
            self.err("type parameters use brackets", f"write fn {name}[T](...)")
        self.tparams = tparams
        self.expect_op("(")
        params: list[Param] = []
        while not self.at_op(")"):
            mut = False
            if self.at_kw("mut"):
                self.advance()
                mut = True
            p = self.expect_ident("parameter name")
            self.expect_op(":", "every parameter needs a type: name: T")
            params.append(Param(p.value, self.type_(), mut, p.line, p.col))
            if not self.at_op(")"):
                self.expect_op(",")
        self.advance()
        ret: Type = "unit"
        if self.at_op("->"):
            self.advance()
            ret = self.type_()
        effects: list[str] = []
        if self.at_op("!"):
            self.advance()
            effects.append(self.expect_ident("effect name").value)
            while self.at_op(","):
                self.advance()
                effects.append(self.expect_ident("effect name").value)
        self.skip_nl()
        requires: list[Expr] = []
        ensures: list[Expr] = []
        while self.at_kw("requires") or self.at_kw("ensures"):
            which = self.advance().value
            (requires if which == "requires" else ensures).append(self.expr())
            self.skip_nl()
        body = self.block()
        self.end_label(name, "fn")
        self.tparams = []
        return FnDef(name, tparams, params, ret, effects, requires, ensures, body, kw.line, kw.col)

    def test_def(self) -> TestDef:
        kw = self.advance()
        name = self.expect_ident("test name").value
        body = self.block()
        self.end_label(name, "test")
        return TestDef(name, body, kw.line, kw.col)

    def type_(self) -> Type:
        if self.at_op("["):
            self.advance()
            inner = self.type_()
            self.expect_op("]")
            return ("arr", inner)
        t = self.expect_ident("type")
        if t.value in PRIMS:
            return t.value
        if t.value in GENERIC_TYPES:
            if self.at_op("<"):
                self.err(f"type arguments use brackets", f"write {t.value}[T]")
            self.expect_op("[", f"write {t.value}[T]")
            inner = self.type_()
            if self.at_op(","):
                hint = "Result[T] carries a str error; drop the second type" if t.value == "Result" else None
                self.err(f"{t.value} takes one type argument", hint)
            self.expect_op("]")
            return (GENERIC_TYPES[t.value], inner)
        if t.value in self.tparams:
            return ("tp", t.value)
        return ("struct", t.value)

    # ---------- statements ----------

    def block(self) -> Block:
        lb = self.expect_op("{", "blocks start with '{' on the same line")
        self.skip_nl()
        stmts: list[Stmt] = []
        while not self.at_op("}"):
            if self.at("EOF"):
                self.err("unexpected end of file inside block", "add the missing '}'", lb)
            stmts.append(self.stmt())
        self.advance()
        return Block(stmts, lb.line)

    def stmt(self) -> Stmt:
        t = self.tok
        if self.at_kw("let"):
            self.advance()
            mut = False
            if self.at_kw("mut"):
                self.advance()
                mut = True
            if self.at("IDENT") and self.tok.value == "_":
                name = self.advance().value
            else:
                name = self.expect_ident("variable name").value
            ann = None
            if self.at_op(":"):
                self.advance()
                ann = self.type_()
            self.expect_op("=", "variables must be initialized: let x = value")
            value = self.expr()
            self.end_stmt()
            return Let(t.line, t.col, name, mut, ann, value)
        if self.at_kw("if"):
            s = self.if_stmt()
            self.end_stmt()
            return s
        if self.at_kw("match"):
            s = self.match_stmt()
            self.end_stmt()
            return s
        if self.at_kw("while"):
            self.advance()
            cond = self.expr()
            body = self.block()
            self.end_stmt()
            return While(t.line, t.col, cond, body)
        if self.at_kw("for"):
            self.advance()
            var = self.expect_ident("loop variable").value
            self.expect_kw("in")
            start = self.add()
            self.expect_op("..", "for loops iterate over a range: for i in 0..n")
            stop = self.add()
            body = self.block()
            self.end_stmt()
            return For(t.line, t.col, var, start, stop, body)
        if self.at_kw("ret"):
            self.advance()
            value = None
            if not (self.at("NL") or self.at_op("}")):
                value = self.expr()
            self.end_stmt()
            return Ret(t.line, t.col, value)
        if self.at_kw("break"):
            self.advance()
            self.end_stmt()
            return Break(t.line, t.col)
        if self.at_kw("continue"):
            self.advance()
            self.end_stmt()
            return Continue(t.line, t.col)
        if self.at("IDENT") and self.tok.value == "return":
            self.err("unknown statement 'return'", "use 'ret'")
        e = self.expr()
        if self.tok.kind == "OP" and self.tok.value in ASSIGN_OPS:
            op = self.advance().value
            value = self.expr()
            self.end_stmt()
            return Assign(t.line, t.col, e, op, value)
        self.end_stmt()
        return ExprStmt(t.line, t.col, e)

    def match_stmt(self) -> Match:
        t = self.advance()
        subject = self.expr()
        self.expect_op("{", "write match x { Pattern => ... }")
        self.skip_nl()
        arms: list[Arm] = []
        while not self.at_op("}"):
            if self.at("EOF"):
                self.err("unexpected end of file inside match", "add the missing '}'", t)
            arms.append(self.arm())
        self.advance()
        return Match(t.line, t.col, subject, arms)

    def arm(self) -> Arm:
        t = self.tok
        enum, variant = None, None
        if self.at("IDENT") and t.value == "_":
            self.advance()
        else:
            first = self.expect_ident("pattern")
            if self.at_op(":") and self.peek().kind == "OP" and self.peek().value == ":":
                self.err("use '.' between enum and variant", f"write {first.value}.Variant")
            if self.at_op("."):
                self.advance()
                enum, variant = first.value, self.expect_ident("variant name").value
            elif first.value in BUILTIN_VARIANTS:
                variant = first.value
            elif first.value[:1].isupper():
                self.err(f"pattern '{first.value}' must name its enum",
                         f"write EnumName.{first.value}", first)
            else:
                self.err(f"expected a pattern (Enum.Variant, Some, None, Ok, Err or _), found '{first.value}'",
                         tok=first)
        binds: list[tuple[str, int, int]] = []
        if variant is not None and self.at_op("("):
            self.advance()
            while not self.at_op(")"):
                b = self.expect_ident("binding name")
                binds.append((b.value, b.line, b.col))
                if not self.at_op(")"):
                    self.expect_op(",", "patterns bind names only: Variant(a, b)")
            self.advance()
        if self.at_kw("if"):
            self.err("match guards are not supported", "put an if inside the arm")
        self.expect_op("=>", "write Pattern => { ... }")
        if self.at_op("{"):
            body = self.block()
            if self.at_op(","):
                self.advance()
            if not (self.at("NL") or self.at_op("}")):
                self.err(f"expected end of line after match arm, found {self.describe()}")
            self.skip_nl()
        else:
            if self.at("NL"):
                self.err("match arm body must start on the same line as '=>'")
            line = self.tok.line
            saved, self.in_arm = self.in_arm, True
            st = self.stmt()
            self.in_arm = saved
            body = Block([st], line)
        return Arm(enum, variant, binds, body, t.line, t.col)

    def if_stmt(self) -> If:
        t = self.advance()
        cond = self.expr()
        then = self.block()
        els = None
        if self.at_kw("else"):
            self.advance()
            if self.at_kw("if"):
                inner = self.if_stmt()
                els = Block([inner], inner.line)
                els.is_elif = True
            else:
                els = self.block()
        return If(t.line, t.col, cond, then, els)

    # ---------- expressions ----------

    def expr(self) -> Expr:
        return self.or_()

    def or_(self) -> Expr:
        left = self.and_()
        while self.at_kw("or"):
            t = self.advance()
            right = self.and_()
            for side in (left, right):
                if isinstance(side, Binary) and side.op == "and" and not side.paren:
                    self.err("mixing 'and' and 'or' needs parentheses",
                             "write (a and b) or c", t)
            left = Binary(t.line, t.col, "or", left, right)
        return left

    def and_(self) -> Expr:
        left = self.not_()
        while self.at_kw("and"):
            t = self.advance()
            right = self.not_()
            if isinstance(right, Binary) and right.op == "or" and not right.paren:
                self.err("mixing 'and' and 'or' needs parentheses", "write a and (b or c)", t)
            left = Binary(t.line, t.col, "and", left, right)
        return left

    def not_(self) -> Expr:
        if self.at_kw("not"):
            t = self.advance()
            return Unary(t.line, t.col, "not", self.not_())
        return self.cmp()

    def cmp(self) -> Expr:
        left = self.add()
        if self.tok.kind == "OP" and self.tok.value in CMP_OPS:
            t = self.advance()
            right = self.add()
            if self.tok.kind == "OP" and self.tok.value in CMP_OPS:
                self.err("comparisons cannot be chained", "write a < b and b < c")
            return Binary(t.line, t.col, t.value, left, right)
        return left

    def add(self) -> Expr:
        left = self.mul()
        while self.tok.kind == "OP" and self.tok.value in ("+", "-"):
            t = self.advance()
            left = Binary(t.line, t.col, t.value, left, self.mul())
        return left

    def mul(self) -> Expr:
        left = self.unary()
        while self.tok.kind == "OP" and self.tok.value in ("*", "/", "%"):
            t = self.advance()
            left = Binary(t.line, t.col, t.value, left, self.unary())
        return left

    def unary(self) -> Expr:
        if self.at_op("-"):
            t = self.advance()
            operand = self.unary()
            if isinstance(operand, Int) and not operand.paren:
                operand.value = -operand.value
                operand.line, operand.col = t.line, t.col
                return operand
            if isinstance(operand, Float) and not operand.paren:
                operand.value = -operand.value
                operand.text = "-" + operand.text
                operand.line, operand.col = t.line, t.col
                return operand
            return Unary(t.line, t.col, "-", operand)
        if self.at_op("!"):
            self.err("'!' is not a negation operator", "use 'not'")
        return self.postfix()

    def postfix(self) -> Expr:
        e = self.primary()
        while True:
            if self.at_op("["):
                t = self.advance()
                idx = self.expr()
                self.expect_op("]")
                e = Index(t.line, t.col, e, idx)
            elif self.at_op("."):
                t = self.advance()
                name = self.expect_ident("field name").value
                if isinstance(e, Name) and not e.paren and e.name[:1].isupper():
                    e = Variant(e.line, e.col, e.name, name, self.call_args() if self.at_op("(") else None)
                else:
                    e = Field(t.line, t.col, e, name)
            elif self.at_op("?"):
                t = self.advance()
                e = Try(t.line, t.col, e)
            elif self.at_op(":") and self.peek().kind == "OP" and self.peek().value == ":":
                self.err("use '.' between enum and variant", "write Enum.Variant")
            else:
                return e

    def call_args(self) -> list[Expr]:
        self.advance()  # (
        out: list[Expr] = []
        while not self.at_op(")"):
            if self.at_kw("mut"):
                self.err("variant arguments cannot be mut")
            out.append(self.expr())
            if not self.at_op(")"):
                self.expect_op(",")
        self.advance()
        return out

    def primary(self) -> Expr:
        t = self.tok
        if t.kind == "INT":
            self.advance()
            v = int(t.value)
            if v > INT_MAX + 1:
                self.err("integer literal does not fit in i64", tok=t)
            return Int(t.line, t.col, v)
        if t.kind == "FLOAT":
            self.advance()
            return Float(t.line, t.col, float(t.value), t.value)
        if t.kind == "STR":
            self.advance()
            return Str(t.line, t.col, t.value)
        if self.at_kw("true") or self.at_kw("false"):
            self.advance()
            return Bool(t.line, t.col, t.value == "true")
        if self.at_op("("):
            self.advance()
            e = self.expr()
            self.expect_op(")")
            e.paren = True
            return e
        if self.at_op("["):
            self.advance()
            elems: list[Expr] = []
            while not self.at_op("]"):
                elems.append(self.expr())
                if not self.at_op("]"):
                    self.expect_op(",")
            self.advance()
            return ArrayLit(t.line, t.col, elems)
        if t.kind == "IDENT" and t.value in BUILTIN_VARIANTS:
            self.advance()
            args = self.call_args() if self.at_op("(") else None
            return Variant(t.line, t.col, None, t.value, args)
        if t.kind == "IDENT":
            self.advance()
            if self.at_op("("):
                self.advance()
                args: list[Arg] = []
                while not self.at_op(")"):
                    mut = False
                    if self.at_kw("mut"):
                        self.advance()
                        mut = True
                    args.append(Arg(self.expr(), mut))
                    if not self.at_op(")"):
                        self.expect_op(",")
                self.advance()
                return Call(t.line, t.col, t.value, args)
            if self.at_op("{") and t.value[:1].isupper() and self.looks_like_struct_lit():
                return self.struct_lit(t)
            return Name(t.line, t.col, t.value)
        self.err(f"expected expression, found {self.describe()}")
        raise AssertionError

    def looks_like_struct_lit(self) -> bool:
        j = self.i + 1
        while self.toks[j].kind == "NL":
            j += 1
        a, b = self.toks[j], self.toks[j + 1]
        return (a.kind == "OP" and a.value == "}") or (a.kind == "IDENT" and b.kind == "OP" and b.value == ":")

    def struct_lit(self, name_tok: Tok) -> StructLit:
        self.advance()  # {
        fields: list[tuple[str, Expr, int, int]] = []
        self.skip_nl()
        while not self.at_op("}"):
            f = self.expect_ident("field name")
            self.expect_op(":")
            fields.append((f.value, self.expr(), f.line, f.col))
            if self.at_op(","):
                self.advance()
            self.skip_nl()
        self.advance()
        return StructLit(name_tok.line, name_tok.col, name_tok.value, fields)


def parse(src: str) -> Program:
    return Parser(lex(src)).program()


def show(e: Expr) -> str:
    """Render an expression back to source (for messages)."""
    def go(x: Expr) -> str:
        s = inner(x)
        return f"({s})" if x.paren else s

    def inner(x: Expr) -> str:
        if isinstance(x, Int):
            return str(x.value)
        if isinstance(x, Float):
            return x.text
        if isinstance(x, Bool):
            return "true" if x.value else "false"
        if isinstance(x, Str):
            return '"' + x.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        if isinstance(x, Name):
            return x.name
        if isinstance(x, Binary):
            return f"{go(x.left)} {x.op} {go(x.right)}"
        if isinstance(x, Unary):
            return f"not {go(x.operand)}" if x.op == "not" else f"-{go(x.operand)}"
        if isinstance(x, Call):
            return f"{x.name}(" + ", ".join(("mut " if a.mut else "") + go(a.expr) for a in x.args) + ")"
        if isinstance(x, Index):
            return f"{go(x.base)}[{go(x.index)}]"
        if isinstance(x, Field):
            return f"{go(x.base)}.{x.name}"
        if isinstance(x, StructLit):
            return x.name + "{" + ", ".join(f"{n}: {go(v)}" for n, v, _, _ in x.fields) + "}"
        if isinstance(x, ArrayLit):
            return "[" + ", ".join(go(v) for v in x.elems) + "]"
        if isinstance(x, Variant):
            s = f"{x.enum}.{x.name}" if x.enum else x.name
            return s if x.args is None else s + "(" + ", ".join(go(v) for v in x.args) + ")"
        if isinstance(x, Try):
            return go(x.operand) + "?"
        return "?"

    return go(e)
