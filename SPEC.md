# aimy language reference (v0.2)

This file is written to be pasted into an AI's context before it writes aimy code.

## Program shape

A file holds `struct`, `enum`, `fn` and `test` definitions in any order. Every top-level
definition closes with `} end NAME` on one line. A runnable program has `fn main() ! io`.

```
struct Point { x: f64, y: f64 } end Point

fn dist(a: Point, b: Point) -> f64 {
  let dx = a.x - b.x
  let dy = a.y - b.y
  ret sqrt(dx * dx + dy * dy)
} end dist

fn main() ! io {
  print(dist(Point{x: 0.0, y: 0.0}, Point{x: 3.0, y: 4.0}))
} end main

test dist {
  dist(Point{x: 0.0, y: 0.0}, Point{x: 3.0, y: 4.0}) == 5.0
} end dist
```

## Types

`i64` `f64` `bool` `str` `[T]` (growable array), structs, enums, `Option[T]`, `Result[T]`.
Type names start uppercase; variable, parameter and fn names start lowercase.
No null, no implicit conversion: use `f64(i)` and `i64(x)` (truncates).
`i64` arithmetic traps on overflow and division by zero.
`==` / `!=` work on `i64 f64 bool str` and on structs, enums, Option and Result built
from them (not on arrays). `< <= > >=` only on `i64` and `f64`.

## Enums and match

```
enum Shape {
  Circle(f64)          # payloads are positional types
  Rect(f64, f64)
  Empty
} end Shape

let s = Shape.Rect(2.0, 3.0)     # always Enum.Variant; no payload: Shape.Empty
match s {
  Shape.Circle(r) => ret 3.0 * r * r
  Shape.Rect(w, h) => {
    print(w)
    ret w * h
  }
  _ => ret 0.0                   # optional catch-all, must be last
}
```

- `match` is a statement, not an expression: arms `ret`, assign, or call. An arm body is
  one statement on the same line after `=>`, or a `{ }` block.
- Patterns: `Enum.Variant(a, b)` binds every payload by position (`_` ignores one);
  `Some(x)` `None` `Ok(x)` `Err(msg)`; `_`. No nested patterns, no guards, no literals.
- Every variant must be covered (or `_` given). Duplicate arms and a `_` that covers
  nothing are errors. A match counts as one nesting level.
- `break` / `continue` inside an arm act on the enclosing loop.
- Bindings are read-only. Enums and structs cannot contain themselves; use `[T]`.

## Option and Result

```
fn find(xs: [i64], t: i64) -> Option[i64] {
  for i in 0..len(xs) {
    if xs[i] == t { ret Some(i) }
  }
  ret None
} end find

fn parse_age(n: i64) -> Result[i64] {      # the error is always a str
  if n < 0 { ret Err("negative age") }
  ret Ok(n)
} end parse_age

fn older(n: i64) -> Result[i64] {
  let a = parse_age(n)?                    # on Err: return that Err from older
  ret Ok(a + 1)
} end older
```

- `Some(x)` `None` `Ok(x)` `Err("msg")`. `None` and `Err` need a known type: `ret`, an
  argument, or an annotation `let x: Option[i64] = None`.
- `e?` unwraps `Some`/`Ok`; on `None`/`Err` it returns it from the current fn, which must
  return `Option[...]` / `Result[...]` (same kind). Not allowed in tests.
- A `Result` must be handled: a statement `f()` or `let _ = f()` returning Result is an error.
- In tests compare directly: `parse_age(-1) == Err("negative age")`.

## Generic functions

```
fn last[T](xs: [T]) -> Option[T] {
  if len(xs) == 0 { ret None }
  ret Some(copy(xs[len(xs) - 1]))
} end last
```

- Type parameters go in `[ ]` after the name and are inferred at each call: `last([1, 2])`.
- Inside the fn a `T` value can be stored, passed, returned, put in arrays and Options,
  but not compared, printed or used in arithmetic.
- A `T` may be an array, so storing an existing `T` place needs `copy()`, as for arrays:
  `ret copy(d)` for a parameter `d: T`, `ret copy(xs[i])` for an element.
- A generic fn may not call itself with different type arguments (`f([x])` inside `f[T]`).

## Statements (one per line)

```
let x = 1                 # immutable, type inferred
let mut xs: [i64] = []    # mutable; empty arrays need a type
x = 2   x += 1            # only on mut variables (also -= *= /= %=)
if c { } else if d { } else { }
while c { }   for i in 0..n { }   break   continue
ret value                 # 'ret' alone in fns without a return type
let _ = f()               # discard a value explicitly
```

## Functions

```
fn name(a: i64, mut out: [i64]) -> i64 ! io
  requires a >= 0
  ensures result >= a
{
  ...
} end name
```

- Parameters are read-only. `mut` parameters are passed by reference and the
  caller must write `mut` too: `name(1, mut xs)`.
- `! io` is required to call `print`, `arg`, `clock` or another `! io` fn.
- `requires` / `ensures` are checked at runtime (`result` = return value).
- Every path of a fn with a return type must `ret`.

## Arrays and copies

Arrays are heap data. Storing an existing array (or a struct that contains one)
into a variable, field, element or return value is an error; write `copy(x)` to make
an independent copy. Exception: inside `ret`, a local variable moves (it dies at `ret`), so `ret x`,
`ret Some(x)`, `ret Pair{a: x}` need no `copy`; using the same local twice in one `ret` does. Parameters and elements never move: `ret p`, `ret xs[i]` of an array, struct or `T` need `copy(p)`, `copy(xs[i])`. Passing it as a normal argument
is free and never copies.
One call may not pass the same variable as `mut` and also in another argument.

## Builtins

| call | meaning |
|---|---|
| `print(a, b, ...)` | print i64/f64/bool/str separated by spaces (`! io`) |
| `len(xs)` | length |
| `push(mut xs, v)` / `pop(mut xs)` | append / remove last |
| `fill(n, v)` | new array of n copies of v |
| `copy(x)` | deep copy |
| `sqrt(x)` `abs(x)` `min(a, b)` `max(a, b)` | math |
| `f64(i)` `i64(x)` | conversion |
| `arg(i)` | i-th command-line argument as i64 (`! io`) |
| `clock()` | monotonic seconds as f64 (`! io`) |
| `assert(c)` | runtime check |

## Rules that catch bugs at compile time

- no shadowing, no unused values, no `and`/`or` mix without parentheses,
  no chained comparisons
- blocks nest at most 3 levels inside a fn; extract a fn instead
- string operations, file io, closures, methods: not in v0.2

## Tests

In a `test` block every line that is a `bool` expression is an assertion.
Failures report the source text and, for comparisons, both sides' values.

## Tooling

All compiler output is JSON lines:

```
aimy check f.aim      {"code","msg","line","col","hint","severity"} per problem
aimy test f.aim       {"test","status",...} per test, then {"summary":...}
aimy run f.aim ARGS   runtime errors: {"error":"runtime","kind",...} on stderr, exit 101
aimy build f.aim [-o out] [--fast]    --fast removes overflow/bounds/contract checks
aimy emit-c f.aim     generated C
```

## Portability

The compiler needs Python 3.12+ and a C compiler named `gcc` or `cc` (gcc on Linux/WSL,
Apple clang on macOS). Generated C is built with `-std=gnu11 -O2 -ffp-contract=off`.
`-ffp-contract=off` disables fused multiply-add, so `f64` results are bit-identical
across x86 gcc and arm64 clang. Programs must not depend on any other float behavior.
