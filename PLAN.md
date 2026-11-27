# aimy plan

## Goal

A language that AIs write and AIs read. Humans are not the audience.
Three targets, in priority order when they conflict:

1. **Fewer bugs**: reject at compile time what can be rejected; trap at runtime the rest.
2. **Faster generation**: few tokens, one way to write each thing, short write-check-fix loops.
3. **Fast execution**: native code through C, safety checks cheap enough to keep on.

## Design principles

- **Familiar surface, AI-specific rules.** Models learned from human code, so keywords
  look like Rust/Go (`fn`, `let`, `if`). The differences are in the rules, not the syntax.
- **Explicit at boundaries, inferred inside.** Signatures carry types, `mut`, effects
  and contracts. Local variable types are inferred.
- **Local reasoning.** The meaning of a line is decidable from nearby text: no globals,
  no shadowing, no implicit conversion, `mut` visible at the call site, no silent aliasing.
- **Structure an AI can't lose track of.** `} end NAME` closes top-level definitions;
  nesting is limited to 3 levels.
- **Machine-readable feedback.** Every diagnostic, test result and runtime error is a
  JSON line with a location and, where possible, a concrete fix (`hint`).

## Status

### v0.1 (done)

- Lexer, parser, type checker, C code generator, C runtime, CLI (`check` `test` `run`
  `build` `emit-c`, `--fast`)
- Types: `i64` `f64` `bool` `str` `[T]` structs
- Safety: checked overflow / bounds / division, contracts, effects, copy rule, alias rule
- Examples: fib, sieve, nbody (matches reference output); 23 pytest cases
- Speed: 15-120x faster than CPython with checks on
- Portable: tested on macOS arm64 (Apple clang) and WSL2 (gcc). `-ffp-contract=off`
  keeps `f64` output identical across both; the binary cache key includes the C flags.
  23 pytest cases pass on macOS. WSL re-run after the flag change is not yet done.

### v0.2 (done)

- `enum` with positional payloads, `Enum.Variant` construction, exhaustive `match`
  statement (E710 missing, E709 duplicate, E708 useless `_`), `break`/`continue` in arms
- `Option[T]` / `Result[T]` (error is always `str`), `Some/None/Ok/Err`, `?` propagation;
  an unhandled or `let _`-discarded `Result` is E711
- Generic fns `fn f[T](...)`, inferred at the call, monomorphized in C; values of `T`
  count as heavy (need `copy()`), cannot be compared; polymorphic recursion is E714
- `==` on structs/enums/Option/Result without arrays; failed test assertions print them
  (`Some("a")`, `Shape.Circle(1.0)`)
- `ret` moves every local it stores once (`ret Some(xs)` needs no copy); variable names
  must start lowercase (E204); Rust habits (`::`, bare `Circle(r)` pattern,
  `Result[T, E]`, `fn f<T>`, expression arms) get E002/E307 hints
- Codegen registers C types lazily, so generic instances emit their own types
- Example `examples/shapes.aim`; 47 pytest cases; benchmarks unchanged vs v0.1

### Evaluation harness (built and run once with kiro-cli)

- `eval/tasks/*`: 19 tasks (`task.md` + hidden `tests.aim`); `eval/refs.txt`: reference
  solutions, all 19 pass (`uv run python eval/run.py --ref`). So tasks fit v0.1 and step 2 below
  is not triggered.
- `uv run python eval/run.py [--rounds N] [--tasks a,b]`: model command from `$AIMY_EVAL_CMD`
  (default `kiro-cli chat --no-interactive --trust-tools= {prompt}`). Writes `eval/results.jsonl`.
- Run 1 (kiro-cli, 19 tasks, 3 fix rounds): first-try compile 18/19, first-try pass 18/19,
  final pass 19/19, 0.05 fix rounds per task. The only failure was `prefix_sums`
  (fixed in 1 round). These tasks are too easy to separate rules; next run needs harder
  tasks (string/enum/Result once they exist) and a Python/Rust baseline.
- Fixed: `ret local_array` is now a move (was E404, forced a wasted `copy`); SPEC updated,
  24 pytest cases pass. Likely cause of the `prefix_sums` first-try failure.
- Other findings: `!` gives E002 with hint `not`; arrays cannot be
  compared with `==`, so tests use a `same()` helper.
- v0.2 added 10 tasks using enum/match/Option/Result/generics (29 total, all refs pass).
  Writing the `min_pos` ref hit the nesting limit (for > if > match > if = 4).
- Run 2 (kiro-cli, v0.2, 29 tasks, `eval/results-v0.2.jsonl`): first-try compile 27/29,
  first-try pass 27/29, final 29/29, 0.07 fix rounds. All 9 enum/Option/Result tasks
  passed first try. Failures: `last_or` (generic) and `sort` (did not reproduce in 3 reruns).
  `last_or` reruns: E404 in 2 of 4 attempts (`ret d` / `ret xs[i]` on a `T` value without
  `copy()`). The harness now records `first_fail` (codes or failing test lines).
- Decided: keep the `T`-needs-`copy()` rule (implicit copy would hide a cost and make
  `T` differ from concrete arrays). E404 on a value that is heavy only through a type
  parameter now says so ("a type parameter can be an array"); SPEC states that parameters
  and elements never move (`ret copy(d)`, `ret copy(xs[i])`). `last_or` rerun 6 times
  (`eval/results-last_or-v0.2.1.jsonl`): first-try pass 6/6 (was 2/4). 48 pytest cases.

- Python baseline: `eval/mk_py.py` writes `task.py.md` + `tests.py` per task (Result errors
  become `raise ValueError(msg)`, Option becomes `None`, enums become Enum/dataclasses,
  contracts become stated preconditions). `eval/pyjudge.py` prints JSON lines like `aimy test`
  (failed `assert a == b` shows the actual value). `eval/run.py --lang py`; Python refs in
  `eval/refs-py.txt`, 29/29 pass. Python tests also check that `reverse`/`count_unique` leave
  the input unchanged (aimy guarantees it by type); both sets now test `safe_div(-7, 2) == -3`.
- Run 3 (kiro-cli, same model, 29 tasks, 3 fix rounds):
  aimy (`eval/results-v0.2.1.jsonl`): first-try pass 28/29, final 29/29, 6941 chars out.
  Python (`eval/results-py-v0.2.1.jsonl`): first-try pass 29/29, final 29/29, 5489 chars out.
  The only aimy failure was `min_pos`: E302 nesting limit, fixed in 1 round (the second time
  the limit bit on this task, after the ref). On these tasks aimy shows no bug advantage over
  Python and costs about 26% more output; the tasks do not exercise the bug classes aimy
  rejects (overflow, aliasing, mutation of inputs, unhandled errors).
- Rust baseline: `eval/mk_rs.py` writes `task.rs.md` + `tests.rs` (slices for arrays,
  `Result<T, String>`, derives given in the task). `eval/rsjudge.py` builds with
  `rustc --edition 2021 --test -C overflow-checks=on -C opt-level=1` (rustc 1.100 via rustup,
  `~/.cargo/bin`) and reports rustc's JSON diagnostics. `eval/run.py --lang rs`; refs in
  `eval/refs-rs.txt`, 29/29 pass. Run 3 Rust (`eval/results-rs-v0.2.1.jsonl`): first-try
  pass 29/29, final 29/29, 6443 chars out.
  Summary of run 3, first-try pass / chars out: aimy 28/29 / 6941, Rust 29/29 / 6443,
  Python 29/29 / 5489.

- Hard set: `eval/mk_hard.py` writes 10 tasks in all three languages from one table, so the
  statements match; names in `eval/hard.txt`, run with `--tasks @hard.txt` (a default run
  now has 39 tasks). Each targets a bug class: `median` (input mutation, overflow of the
  middle pair), `mid` (overflow of a + b, rounding of negatives), `mul_mod` (a * b overflow,
  m up to 10^18), `identity` (row aliasing), `local_peaks` (ends; Python `xs[-1]` wraps),
  `rotate` (negative and huge k, `%` on negatives), `transfer` (negative indices, check order,
  no change on error), `transfer_all` (all or nothing), `avg_i64` (exact mean when the sum
  overflows), `hist` (values below lo, truncating vs floor division). Only `median`'s test
  checks an unstated invariant (input order kept, Python only). Refs in all three languages
  pass 10/10. Checked that a typical buggy solution fails the hidden tests for 7 tasks in Python
  (median, mid, identity, local_peaks, transfer, avg_i64, hist) and 2 in aimy (mid, mul_mod trap on
  overflow). Fixed on the way: `pyjudge.py` now evaluates `got` in the test's own frame.
- Run 4 (hard set, kiro-cli, `eval/results-hard-{aimy,py,rs}.jsonl`): first-try pass
  10/10 in every language. Chars out: aimy 3042, Rust 2900, Python 2335. When the statement
  names the edge cases, this model handles them in any language, so stated edge cases do not
  separate the languages either. aimy rejected nothing the model wrote.

- Terse variant: `eval/mk_hard.py` also writes `tasks/<name>_terse` (same hidden tests;
  the statement keeps result, error messages, check order and preconditions, and drops every
  sentence that points at an edge case). Names in `eval/hard-terse.txt`; refs fall back to
  the base task. Refs pass 10/10 in all three languages.
- Run 5 (terse set, kiro-cli, 2 runs per language, `eval/results-terse-{aimy,py,rs}-r{1,2}.jsonl`):
  first-try pass aimy 9/10 and 9/10, Python 10/10 and 10/10, Rust 10/10 and 10/10; final
  10/10 everywhere. Chars out: aimy 3384 / 3570, Rust 3309 / 3268, Python 2190 / 2182.
  Both aimy failures were `avg_i64_terse`: the i64 sum overflowed and trapped at test time
  (`first_fail: ["overflow"]`), fixed in 1 round. Rust passed the same task first try and
  Python has no overflow, so the trap found a bug that the other languages did not have:
  aimy has no wider integer type (Rust can use i128).
  `mid_terse` passed first try in aimy too: the model avoided `a + b` without being told.

## Next steps (decided order)

1. Make the eval able to separate languages. Tried: dropping edge cases from the
   statement (run 5, no separation except aimy's missing wide integer). Left: larger
   multi-function tasks where bugs come from interactions; a weaker or faster model
   via `$AIMY_EVAL_CMD`; repeated runs to measure variance. Until one of these shows a
   difference, the eval gives no reason to keep or drop any aimy rule, and output length
   (aimy longest in runs 3 to 5) is the only measured difference.
2. Nesting limit: 2 of 2 hits were `for > if > match/if` in `min_pos`. Consider raising
   it to 4 or not counting `match` arms, then rerun.
3. v0.3 memory, then v0.4 strings and io.
4. Optional: run `uv run pytest` on WSL to confirm the `-ffp-contract=off` change and v0.2.

## Roadmap

### v0.2: data modelling
- [x] `enum` with payloads and exhaustive `match`
- [x] `Option[T]` / `Result[T]` with `?` propagation; an unhandled `Result` is an error
- [x] Generic functions over a small set of type parameters
- [ ] Open: `match` as an expression? `==` on arrays (would remove `same()` in tests)?
      Typed errors (`Result[T, E]`)? Decide from eval failures.

### v0.3: memory
- [ ] Free memory: compare arena-per-call vs reference counting on the benchmarks
- [ ] Relax the alias rule to allow distinct elements (`mut bs[i]`, `mut bs[j]`) with a runtime check

### v0.4: strings and io
- [ ] String building, slicing, formatting
- [ ] Reading files and stdin under `! io`

### Evaluation (run after every version)
- [x] Task set: about 20 small problems with reference tests (29 after v0.2)
- [ ] Give an AI only SPEC.md, measure: first-try compile rate, fix rounds until tests
      pass, tokens per solution
- [x] Compare the same tasks in Python and Rust (run 3; needs harder tasks to separate them)
- [ ] Use the results to decide which rules to keep, add or drop

### Tooling
- [ ] Report several parse errors per run
- [ ] Per-function check (`aimy check f.aim --fn name`)
- [ ] Rewrite the compiler in a faster language if compile time becomes the bottleneck

## Open questions

- Is the nesting limit of 3 a help or a cost? Measure in the evaluation.
- Should `--fast` keep contracts?
- Do longer, explicit keywords cost more tokens than they save in fix rounds?
