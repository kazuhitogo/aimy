# aimy

A programming language written by AIs, for AIs.

**The name**: aimy is read "aimai" (曖昧), Japanese for "ambiguous". The language's
whole point is to remove ambiguity, so the name contradicts itself. It is also spelled
"AI-my": my AI. Source files use `.aim`.

- **Fewer bugs**: static types, no implicit conversion, no shadowing, explicit `mut`
  at call sites, explicit `copy()`, declared `! io` effects, contracts, inline tests,
  checked integer overflow and array bounds.
- **Faster generation**: one way to write things, definitions in any order, and every
  diagnostic is JSON with a concrete `hint`, so the write-check-fix loop is short.
- **Fast execution**: compiles to C and then to native code with gcc.

Language reference: [SPEC.md](SPEC.md). Roadmap: [PLAN.md](PLAN.md).

## Setup

Requires Python 3.12+, uv and a C compiler (`gcc` or `cc`). Works on Linux, WSL and macOS
(on macOS install Xcode Command Line Tools: `xcode-select --install`).

```
# WSL only: keep the venv on the Linux filesystem (/mnt/c is very slow)
export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/aimy
uv sync
uv run aimy run examples/fib.aim 30
uv run aimy test examples/nbody.aim
uv run pytest
uv run python eval/run.py --ref   # validate eval tasks
uv run python eval/run.py         # run the AI evaluation (needs kiro-cli)
uv run python eval/run.py --lang py  # same tasks in Python (baseline; also --lang rs)
uv run python eval/run.py --tasks @hard.txt  # hard set only
```

## Benchmarks

`bench/run.sh` (WSL2, gcc 15, -O2):

| program | aimy | aimy --fast | CPython 3.14 |
|---|---|---|---|
| fib 32 | 0.25s | 0.09s | 3.94s |
| sieve 20,000,000 | 1.59s | 1.36s | 24.29s |
| nbody 2,000,000 | 1.20s | 1.13s | 144.55s |

## Layout

```
src/aimy/lexer.py    tokens
src/aimy/parser.py   AST
src/aimy/checker.py  types and safety rules
src/aimy/codegen.py  C output
src/aimy/runtime.py  C runtime
src/aimy/cli.py      check / build / run / test / emit-c
```

## Known limits (v0.1)

- Memory is never freed (no GC or ownership yet).
- No enums, `match`, `Result`/`Option`, string operations or generics.
- Parse errors stop at the first one; type errors are all reported.
