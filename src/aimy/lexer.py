"""Tokenizer. Newlines terminate statements, except inside () and []."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import CompileError, Diag

KEYWORDS = {
    "fn", "let", "mut", "if", "else", "while", "for", "in", "ret", "break",
    "continue", "struct", "test", "end", "requires", "ensures", "true", "false",
    "and", "or", "not", "enum", "match",
}

OPS3: set[str] = set()
OPS2 = {"..", "->", "=>", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%="}
OPS1 = set("+-*/%<>=()[]{},:.!?")


@dataclass
class Tok:
    kind: str  # INT FLOAT STR IDENT KW OP NL EOF
    value: str
    line: int
    col: int


ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def lex(src: str) -> list[Tok]:
    toks: list[Tok] = []
    i, line, col = 0, 1, 1
    depth = 0  # () and [] nesting; newlines are ignored inside
    n = len(src)

    def err(msg: str, hint: str | None = None):
        raise CompileError([Diag("E001", msg, line, col, hint)])

    def add(kind: str, value: str, l: int, c: int):
        if kind == "NL":
            if depth > 0 or not toks or toks[-1].kind == "NL":
                return
        toks.append(Tok(kind, value, l, c))

    while i < n:
        ch = src[i]
        if ch == "\n":
            add("NL", "\\n", line, col)
            i += 1
            line += 1
            col = 1
            continue
        if ch in " \t\r":
            i += 1
            col += 1
            continue
        if ch == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue
        start, sl, sc = i, line, col
        if ch.isdigit():
            while i < n and (src[i].isdigit() or src[i] == "_"):
                i += 1
            is_float = False
            if i + 1 < n and src[i] == "." and src[i + 1].isdigit():
                is_float = True
                i += 1
                while i < n and (src[i].isdigit() or src[i] == "_"):
                    i += 1
            if i < n and src[i] in "eE":
                j = i + 1
                if j < n and src[j] in "+-":
                    j += 1
                if j < n and src[j].isdigit():
                    is_float = True
                    i = j
                    while i < n and src[i].isdigit():
                        i += 1
            if i < n and (src[i].isalpha() or src[i] == "_"):
                col += i - start
                err(f"invalid number literal '{src[start:i + 1]}'")
            text = src[start:i].replace("_", "")
            add("FLOAT" if is_float else "INT", text, sl, sc)
            col += i - start
            continue
        if ch.isalpha() or ch == "_":
            while i < n and (src[i].isalnum() or src[i] == "_"):
                i += 1
            word = src[start:i]
            add("KW" if word in KEYWORDS else "IDENT", word, sl, sc)
            col += i - start
            continue
        if ch == '"':
            i += 1
            buf = []
            while True:
                if i >= n or src[i] == "\n":
                    err("unterminated string literal", 'close the string with " on the same line')
                c = src[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\":
                    if i + 1 < n and src[i + 1] in ESCAPES:
                        buf.append(ESCAPES[src[i + 1]])
                        i += 2
                        continue
                    err("invalid escape in string", r"allowed escapes: \n \t \" \\")
                buf.append(c)
                i += 1
            add("STR", "".join(buf), sl, sc)
            col += i - start
            continue
        two = src[i:i + 2]
        if two in OPS2:
            add("OP", two, sl, sc)
            i += 2
            col += 2
            continue
        if ch in OPS1:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth = max(0, depth - 1)
            add("OP", ch, sl, sc)
            i += 1
            col += 1
            continue
        err(f"unexpected character {ch!r}")
    add("NL", "\\n", line, col)
    toks.append(Tok("EOF", "", line, col))
    return toks
