"""AST nodes.

Types are plain values: "i64" "f64" "bool" "unit" "str", ("arr", T), ("struct", Name),
("enum", Name), ("opt", T) = Option[T], ("res", T) = Result[T], ("tp", Name) = type parameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Type = Any


def type_str(t: Type) -> str:
    if isinstance(t, tuple):
        if t[0] == "arr":
            return f"[{type_str(t[1])}]"
        if t[0] == "opt":
            return f"Option[{type_str(t[1])}]"
        if t[0] == "res":
            return f"Result[{type_str(t[1])}]"
        return t[1]
    return t


def subst(t: Type, sub: dict[str, Type]) -> Type:
    """Replace type parameters."""
    if not sub or not isinstance(t, tuple):
        return t
    if t[0] == "tp":
        return sub.get(t[1], t)
    if t[0] in ("arr", "opt", "res"):
        return (t[0], subst(t[1], sub))
    return t


def has_tp(t: Type) -> bool:
    if not isinstance(t, tuple):
        return False
    if t[0] == "tp":
        return True
    return t[0] in ("arr", "opt", "res") and has_tp(t[1])


# ---------- expressions ----------

@dataclass(eq=False)
class Expr:
    line: int
    col: int

    def __post_init__(self):
        self.ty: Type = None
        self.paren = False


@dataclass(eq=False)
class Int(Expr):
    value: int


@dataclass(eq=False)
class Float(Expr):
    value: float
    text: str


@dataclass(eq=False)
class Bool(Expr):
    value: bool


@dataclass(eq=False)
class Str(Expr):
    value: str


@dataclass(eq=False)
class Name(Expr):
    name: str


@dataclass(eq=False)
class Binary(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass(eq=False)
class Unary(Expr):
    op: str
    operand: Expr


@dataclass(eq=False)
class Arg:
    expr: Expr
    mut: bool


@dataclass(eq=False)
class Call(Expr):
    name: str
    args: list[Arg]


@dataclass(eq=False)
class Index(Expr):
    base: Expr
    index: Expr


@dataclass(eq=False)
class Field(Expr):
    base: Expr
    name: str


@dataclass(eq=False)
class StructLit(Expr):
    name: str
    fields: list[tuple[str, Expr, int, int]]


@dataclass(eq=False)
class ArrayLit(Expr):
    elems: list[Expr]


@dataclass(eq=False)
class Variant(Expr):
    """Enum.Name(args), Enum.Name, Some(x), None, Ok(x), Err(e). enum is None for the builtins."""
    enum: str | None
    name: str
    args: list[Expr] | None


@dataclass(eq=False)
class Try(Expr):
    """e? : unwrap Some/Ok or return None/Err from the enclosing fn."""
    operand: Expr


# ---------- statements ----------

@dataclass(eq=False)
class Stmt:
    line: int
    col: int


@dataclass(eq=False)
class Block:
    stmts: list[Stmt]
    line: int


@dataclass(eq=False)
class Let(Stmt):
    name: str
    mut: bool
    ann: Type | None
    value: Expr


@dataclass(eq=False)
class Assign(Stmt):
    target: Expr
    op: str
    value: Expr


@dataclass(eq=False)
class If(Stmt):
    cond: Expr
    then: Block
    els: Block | None  # else-if is an If wrapped in a Block


@dataclass(eq=False)
class While(Stmt):
    cond: Expr
    body: Block


@dataclass(eq=False)
class For(Stmt):
    var: str
    start: Expr
    stop: Expr
    body: Block


@dataclass(eq=False)
class Arm:
    enum: str | None
    variant: str | None  # None: wildcard '_'
    binds: list[tuple[str, int, int]]
    body: Block
    line: int
    col: int


@dataclass(eq=False)
class Match(Stmt):
    subject: Expr
    arms: list[Arm]


@dataclass(eq=False)
class Ret(Stmt):
    value: Expr | None


@dataclass(eq=False)
class Break(Stmt):
    pass


@dataclass(eq=False)
class Continue(Stmt):
    pass


@dataclass(eq=False)
class ExprStmt(Stmt):
    expr: Expr
    is_assert: bool = False


# ---------- top level ----------

@dataclass(eq=False)
class Param:
    name: str
    ty: Type
    mut: bool
    line: int
    col: int


@dataclass(eq=False)
class StructDef:
    name: str
    fields: list[tuple[str, Type, int, int]]
    line: int
    col: int


@dataclass(eq=False)
class EnumDef:
    name: str
    variants: list[tuple[str, list[Type], int, int]]
    line: int
    col: int


@dataclass(eq=False)
class FnDef:
    name: str
    tparams: list[str]
    params: list[Param]
    ret: Type
    effects: list[str]
    requires: list[Expr]
    ensures: list[Expr]
    body: Block
    line: int
    col: int


@dataclass(eq=False)
class TestDef:
    name: str
    body: Block
    line: int
    col: int


@dataclass(eq=False)
class Program:
    structs: list[StructDef] = field(default_factory=list)
    enums: list[EnumDef] = field(default_factory=list)
    fns: list[FnDef] = field(default_factory=list)
    tests: list[TestDef] = field(default_factory=list)
