"""aimy command line.

  aimy check FILE            type-check, print JSON diagnostics
  aimy build FILE [-o OUT]   compile to a native binary
  aimy run FILE [ARGS...]    compile and run
  aimy test FILE             run the test blocks, one JSON line per test
  aimy emit-c FILE           print the generated C

Add --fast to build/run to remove overflow, bounds and contract checks.
All compiler output on stdout is JSON lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .checker import Checker
from .codegen import generate
from .errors import CompileError, Diag
from .parser import parse

# -ffp-contract=off: no FMA fusion, so float output is identical on x86 gcc and arm64 clang
CC_FLAGS = ["-std=gnu11", "-O2", "-w", "-ffp-contract=off"]


def front(path: str) -> tuple[object, Checker, list[Diag]]:
    try:
        src = Path(path).read_text(encoding="utf-8")
    except OSError as ex:
        raise CompileError([Diag("E000", f"cannot read file: {ex.strerror}", 0, 0)])
    prog = parse(src)
    chk = Checker(prog)
    chk.run()
    return prog, chk, chk.diags


def emit_diags(diags: list[Diag], path: str):
    for d in diags:
        d.src = path
        print(d.to_json())


def compile_c(c_src: str, out: Path, fast: bool) -> None:
    gcc = shutil.which("gcc") or shutil.which("cc")
    if not gcc:
        raise CompileError([Diag("E900", "no C compiler found (need gcc)", 0, 0)])
    flags = CC_FLAGS  # -march=native measured slower on n-body
    with tempfile.TemporaryDirectory() as td:
        cfile = Path(td) / "prog.c"
        cfile.write_text(c_src, encoding="utf-8")
        r = subprocess.run([gcc, *flags, str(cfile), "-o", str(out), "-lm"], capture_output=True, text=True)
    if r.returncode != 0:
        raise CompileError([Diag("E901", "internal compiler error: generated C failed to compile", 0, 0,
                                 r.stderr[-2000:])])


def cache_binary(c_src: str, fast: bool) -> Path:
    key = hashlib.sha256((c_src + str(fast) + " ".join(CC_FLAGS) + __version__).encode()).hexdigest()[:20]
    d = Path(os.environ.get("AIMY_CACHE", Path(tempfile.gettempdir()) / "aimy-cache"))
    d.mkdir(parents=True, exist_ok=True)
    exe = d / key
    if not exe.exists():
        tmp = d / (key + f".tmp{os.getpid()}")
        compile_c(c_src, tmp, fast)
        tmp.replace(exe)
    return exe


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aimy", description="the aimy compiler")
    ap.add_argument("--version", action="version", version=f"aimy {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "build", "run", "test", "emit-c"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name in ("build", "run", "emit-c"):
            p.add_argument("--fast", action="store_true", help="remove runtime safety checks")
        if name == "build":
            p.add_argument("-o", "--output")
        if name in ("run", "test"):
            p.add_argument("args", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)

    try:
        prog, chk, diags = front(a.file)
    except CompileError as ex:
        emit_diags(ex.diags, a.file)
        return 1
    if a.cmd == "check":
        emit_diags(diags, a.file)
        print(json.dumps({"ok": True, "warnings": len(diags)}))
        return 0
    # warnings go to stderr for build/run/test so stdout stays clean
    for d in diags:
        d.src = a.file
        print(d.to_json(), file=sys.stderr)

    fast = getattr(a, "fast", False)
    mode = "test" if a.cmd == "test" else "run"
    if mode == "run" and "main" not in chk.fns:
        emit_diags([Diag("E109", "no 'fn main()' found", 1, 1, "add: fn main() ! io { ... } end main")], a.file)
        return 1
    if mode == "test" and not prog.tests:
        print(json.dumps({"summary": {"passed": 0, "failed": 0}}))
        return 0
    try:
        c_src = generate(prog, chk, mode=mode, checked=not fast)
    except CompileError as ex:
        emit_diags(ex.diags, a.file)
        return 1
    if a.cmd == "emit-c":
        sys.stdout.write(c_src)
        return 0
    try:
        if a.cmd == "build":
            out = Path(a.output or Path(a.file).with_suffix(""))
            compile_c(c_src, out, fast)
            print(json.dumps({"ok": True, "output": str(out)}))
            return 0
        exe = cache_binary(c_src, fast)
    except CompileError as ex:
        emit_diags(ex.diags, a.file)
        return 1
    args = [x for x in a.args if x != "--"]
    sys.stdout.flush()
    return subprocess.call([str(exe), *args])


if __name__ == "__main__":
    sys.exit(main())
