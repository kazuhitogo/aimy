"""Generate the hard task set in all three languages: task.md/tests.aim, task.py.md/tests.py,
task.rs.md/tests.rs. Names are listed in eval/hard.txt (`run.py --tasks @hard.txt`);
the terse variant (see TERSE below) in eval/hard-terse.txt.

Each task targets a bug class aimy is meant to catch. The statement is the same in every
language; only types and the error convention change (aimy/Rust `Err(msg)`, Python
`raise ValueError(msg)`). Hidden tests probe the edge cases the statement mentions.
One test checks an invariant the statement leaves unstated: `median` must not reorder its
input (aimy and Rust make that impossible by type; Python does not).

  median        input mutation, i64 overflow in the middle pair (values are any i64)
  mid           i64 overflow of a + b, rounding direction for negatives
  mul_mod       i64 overflow of a * b with m up to 10^18
  identity      aliasing of rows in a nested array
  local_peaks   off-by-one at the ends (Python's xs[-1] silently wraps)
  rotate        negative / large k, empty input, % on negatives
  transfer      negative indices, check order, no change on error
  transfer_all  all-or-nothing: a later failure must undo earlier transfers
  avg_i64       exact mean when the sum overflows i64, rounding toward zero
  hist          values below lo (truncating vs floor division), right edge
"""
import pathlib

MAX, MIN = "9223372036854775807", "-9223372036854775808"
SAME = """fn same(a: [i64], b: [i64]) -> bool {
  if len(a) != len(b) { ret false }
  for i in 0..len(a) {
    if a[i] != b[i] { ret false }
  }
  ret true
} end same

"""
SAME2 = """fn same2(a: [[i64]], b: [[i64]]) -> bool {
  if len(a) != len(b) { ret false }
  for i in 0..len(a) {
    if not same(a[i], b[i]) { ret false }
  }
  ret true
} end same2

"""
ERR = '''def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

'''

TRANSFER_RULES = ("Move amt from bal[src] to bal[dst]. Checks, in this order: {e}(\"bad account\") if src or dst "
                  "is not a valid index; {e}(\"bad amount\") if amt <= 0; {e}(\"insufficient funds\") if "
                  "bal[src] < amt. src == dst is allowed (same checks, balances unchanged). "
                  "Balances and amounts stay below 10^15.")

T = {}

d = "The median of xs: the middle value after sorting, or the mean of the two middle values for even length. Values can be any i64."
T["median"] = dict(
    aimy=("fn median(xs: [i64]) -> f64\n  requires len(xs) > 0", d,
          f"median([3, 1, 2]) == 2.0\n  median([4, 1, 3, 2]) == 2.5\n  median([5]) == 5.0\n"
          f"  median([-3, -4]) == -3.5\n  median([{MAX}, {MAX}]) == 9223372036854775807.0\n"
          f"  median([{MIN}, {MIN}, 0, 0]) == -4611686018427387904.0"),
    py=("def median(xs: list[int]) -> float", d.replace("Values can be any i64.", "Values can be any i64. Precondition: len(xs) > 0."),
        f"a = [3, 1, 2]\nassert median(a) == 2.0\nassert median([4, 1, 3, 2]) == 2.5\nassert median([5]) == 5.0\n"
        f"assert median([-3, -4]) == -3.5\nassert median([{MAX}, {MAX}]) == 9223372036854775807.0\n"
        f"assert median([{MIN}, {MIN}, 0, 0]) == -4611686018427387904.0\nassert a == [3, 1, 2]"),
    rs=("fn median(xs: &[i64]) -> f64", d + " Precondition: xs.len() > 0.",
        f"assert_eq!(median(&[3, 1, 2]), 2.0);\nassert_eq!(median(&[4, 1, 3, 2]), 2.5);\nassert_eq!(median(&[5]), 5.0);\n"
        f"assert_eq!(median(&[-3, -4]), -3.5);\nassert_eq!(median(&[{MAX}, {MAX}]), 9223372036854775807.0);\n"
        f"assert_eq!(median(&[{MIN}, {MIN}, 0, 0]), -4611686018427387904.0);"),
)

d = "(a + b) / 2 rounded toward zero, exact for every pair of i64 values."
mid_cases = [("1", "2", "1"), ("-1", "-2", "-1"), ("-3", "0", "-1"), ("7", "-2", "2"), (MAX, MAX, MAX),
             (MIN, MIN, MIN), (MAX, MIN, "0"), (MIN, "-9223372036854775807", "-9223372036854775807"),
             (MAX, "9223372036854775806", "9223372036854775806")]
T["mid"] = dict(
    aimy=("fn mid(a: i64, b: i64) -> i64", d, "\n  ".join(f"mid({a}, {b}) == {r}" for a, b, r in mid_cases)),
    py=("def mid(a: int, b: int) -> int", d, "\n".join(f"assert mid({a}, {b}) == {r}" for a, b, r in mid_cases)),
    rs=("fn mid(a: i64, b: i64) -> i64", d, "\n".join(f"assert_eq!(mid({a}, {b}), {r});" for a, b, r in mid_cases)),
)

d = "(a * b) mod m. Precondition: 1 <= m <= 10^18, 0 <= a < m, 0 <= b < m."
mm = [("3", "4", "5", "2"), ("0", "5", "7", "0"), ("0", "0", "1", "0"),
      ("999999999999999999", "999999999999999999", "1000000000000000000", "1"),
      ("100000000000000003", "100000000000000007", "999999999999999989", "110000000000000032"),
      ("999999999999999989", "999999999999999967", "999999999999999993", "104"),
      ("123456789012345678", "987654321098765432", "1000000000000000000", "322511812221002896")]
T["mul_mod"] = dict(
    aimy=("fn mul_mod(a: i64, b: i64, m: i64) -> i64", d, "\n  ".join(f"mul_mod({a}, {b}, {m}) == {r}" for a, b, m, r in mm)),
    py=("def mul_mod(a: int, b: int, m: int) -> int", d, "\n".join(f"assert mul_mod({a}, {b}, {m}) == {r}" for a, b, m, r in mm)),
    rs=("fn mul_mod(a: i64, b: i64, m: i64) -> i64", d, "\n".join(f"assert_eq!(mul_mod({a}, {b}, {m}), {r});" for a, b, m, r in mm)),
)

d = "The n x n identity matrix as a list of rows: 1 on the diagonal, 0 elsewhere. Precondition: n >= 0."
T["identity"] = dict(
    aimy=("fn identity(n: i64) -> [[i64]]", d.replace("list of rows", "array of rows"),
          "let e: [[i64]] = []\n  same2(identity(0), e)\n  same2(identity(1), [[1]])\n"
          "  same2(identity(3), [[1, 0, 0], [0, 1, 0], [0, 0, 1]])"),
    py=("def identity(n: int) -> list[list[int]]", d,
        "assert identity(0) == []\nassert identity(1) == [[1]]\nassert identity(3) == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]\n"
        "g = identity(2)\ng[0][1] = 5\nassert g[1][1] == 1 and g[1][0] == 0"),
    rs=("fn identity(n: i64) -> Vec<Vec<i64>>", d.replace("list of rows", "vector of rows"),
        "assert_eq!(identity(0), Vec::<Vec<i64>>::new());\nassert_eq!(identity(1), vec![vec![1]]);\n"
        "assert_eq!(identity(3), vec![vec![1, 0, 0], vec![0, 1, 0], vec![0, 0, 1]]);"),
)

d = ("Count the indices i where xs[i] is strictly greater than each neighbor that exists "
     "(xs[i-1] and xs[i+1]; the first and last elements have only one neighbor, a single element has none).")
lp = [("[]", "0"), ("[5]", "1"), ("[1, 2]", "1"), ("[2, 1, 2]", "2"), ("[1, 3, 2, 4, 1]", "2"), ("[3, 3]", "0"),
      ("[1, 2, 1, 2]", "2"), ("[2, 1, 1, 2]", "2")]
T["local_peaks"] = dict(
    aimy=("fn local_peaks(xs: [i64]) -> i64", d, "\n  ".join(f"local_peaks({x}) == {r}" for x, r in lp)),
    py=("def local_peaks(xs: list[int]) -> int", d, "\n".join(f"assert local_peaks({x}) == {r}" for x, r in lp)),
    rs=("fn local_peaks(xs: &[i64]) -> i64", d, "\n".join(f"assert_eq!(local_peaks(&{x}), {r});" for x, r in lp)),
)

d = ("Rotate xs right by k places in place: the element at index i moves to index (i + k) mod len. "
     "k can be any i64, including negative (rotate left) and larger than len. An empty xs stays empty.")
rot = [("[1, 2, 3, 4, 5]", "2", "[4, 5, 1, 2, 3]"), ("[1, 2, 3, 4, 5]", "-1", "[2, 3, 4, 5, 1]"),
       ("[1, 2, 3, 4, 5]", "7", "[4, 5, 1, 2, 3]"), ("[1, 2, 3]", "0", "[1, 2, 3]"),
       ("[1, 2, 3, 4, 5]", MIN, "[4, 5, 1, 2, 3]"), ("[1, 2, 3, 4, 5]", MAX, "[4, 5, 1, 2, 3]")]
aimy_rot = "\n  ".join(f"let mut a{i} = {x}\n  rotate(mut a{i}, {k})\n  same(a{i}, {r})" for i, (x, k, r) in enumerate(rot))
T["rotate"] = dict(
    aimy=("fn rotate(mut xs: [i64], k: i64)", d,
          aimy_rot + "\n  let mut e: [i64] = []\n  rotate(mut e, 3)\n  len(e) == 0"),
    py=("def rotate(xs: list[int], k: int) -> None", d,
        "\n".join(f"a = {x}\nrotate(a, {k})\nassert a == {r}" for x, k, r in rot) + "\ne = []\nrotate(e, 3)\nassert e == []"),
    rs=("fn rotate(xs: &mut [i64], k: i64)", d,
        "\n".join(f"let mut a{i} = vec!{x};\nrotate(&mut a{i}, {k});\nassert_eq!(a{i}, vec!{r});" for i, (x, k, r) in enumerate(rot))
        + "\nlet mut e: Vec<i64> = vec![];\nrotate(&mut e, 3);\nassert!(e.is_empty());"),
)

dt = TRANSFER_RULES + " On success return the new balance of bal[src]. On an error bal must be unchanged."
tr = [("[10, 5]", "0", "1", "3", "Ok(7)", "[7, 8]"), ("[10, 5]", "1", "1", "5", "Ok(5)", "[10, 5]"),
      ("[10, 5]", "1", "0", "6", "insufficient funds", "[10, 5]"), ("[10, 5]", "0", "2", "1", "bad account", "[10, 5]"),
      ("[10, 5]", "-1", "0", "1", "bad account", "[10, 5]"), ("[10, 5]", "0", "-1", "1", "bad account", "[10, 5]"),
      ("[10, 5]", "0", "1", "0", "bad amount", "[10, 5]"), ("[10, 5]", "0", "5", "-1", "bad account", "[10, 5]"),
      ("[10, 5]", "1", "1", "6", "insufficient funds", "[10, 5]")]


def tr_aimy(i, b, s, t, a, r, after):
    want = r if r.startswith("Ok") else f'Err("{r}")'
    return f"let mut b{i} = {b}\n  transfer(mut b{i}, {s}, {t}, {a}) == {want}\n  same(b{i}, {after})"


def tr_py(b, s, t, a, r, after):
    call = f"transfer(b, {s}, {t}, {a})"
    check = f"assert {call} == {r[3:-1]}" if r.startswith("Ok") else f'err(lambda: {call}, "{r}")'
    return f"b = {b}\n{check}\nassert b == {after}"


def tr_rs(i, b, s, t, a, r, after):
    want = r if r.startswith("Ok") else f'Err("{r}".to_string())'
    return f"let mut b{i} = vec!{b};\nassert_eq!(transfer(&mut b{i}, {s}, {t}, {a}), {want});\nassert_eq!(b{i}, vec!{after});"


T["transfer"] = dict(
    aimy=("fn transfer(mut bal: [i64], src: i64, dst: i64, amt: i64) -> Result[i64]", dt.format(e="Err"),
          "\n  ".join(tr_aimy(i, *c) for i, c in enumerate(tr))),
    py=("def transfer(bal: list[int], src: int, dst: int, amt: int) -> int", dt.format(e="raise ValueError"),
        "\n".join(tr_py(*c) for c in tr)),
    rs=("fn transfer(bal: &mut [i64], src: i64, dst: i64, amt: i64) -> Result<i64, String>", dt.format(e="Err"),
        "\n".join(tr_rs(i, *c) for i, c in enumerate(tr))),
)

dta = ("Apply the transfers in order. Each one follows these rules: " + TRANSFER_RULES +
       " All or nothing: if any transfer fails, bal must end exactly as it was before the call and the result is that "
       "transfer's error; otherwise return the number of transfers applied.")
ta = [("[10, 0, 0]", [(0, 1, 5), (1, 2, 5)], "Ok(2)", "[5, 0, 5]"),
      ("[10, 0, 0]", [], "Ok(0)", "[10, 0, 0]"),
      ("[10, 0, 0]", [(0, 1, 5), (1, 2, 6)], "insufficient funds", "[10, 0, 0]"),
      ("[10, 0, 0]", [(0, 1, 5), (0, 2, 5), (2, 3, 1)], "bad account", "[10, 0, 0]"),
      ("[10, 0]", [(0, 1, 4), (1, 0, 4), (0, 1, 0)], "bad amount", "[10, 0]")]


def ta_list(ts, mk):
    return "[" + ", ".join(mk(s, t, a) for s, t, a in ts) + "]"


def ta_aimy(i, b, ts, r, after):
    want = r if r.startswith("Ok") else f'Err("{r}")'
    lst = ta_list(ts, lambda s, t, a: f"Transfer{{src: {s}, dst: {t}, amt: {a}}}")
    pre = f"let t{i}: [Transfer] = []\n  " if not ts else ""
    arg = f"t{i}" if not ts else lst
    return f"{pre}let mut b{i} = {b}\n  transfer_all(mut b{i}, {arg}) == {want}\n  same(b{i}, {after})"


def ta_py(b, ts, r, after):
    call = f"transfer_all(b, {ta_list(ts, lambda s, t, a: f'Transfer({s}, {t}, {a})')})"
    check = f"assert {call} == {r[3:-1]}" if r.startswith("Ok") else f'err(lambda: {call}, "{r}")'
    return f"b = {b}\n{check}\nassert b == {after}"


def ta_rs(i, b, ts, r, after):
    want = r if r.startswith("Ok") else f'Err("{r}".to_string())'
    lst = ta_list(ts, lambda s, t, a: f"Transfer {{ src: {s}, dst: {t}, amt: {a} }}")
    return (f"let mut b{i} = vec!{b};\nassert_eq!(transfer_all(&mut b{i}, &{lst}), {want});\n"
            f"assert_eq!(b{i}, vec!{after});")


T["transfer_all"] = dict(
    aimy=("struct Transfer { src: i64, dst: i64, amt: i64 } end Transfer\n\n"
          "fn transfer_all(mut bal: [i64], ts: [Transfer]) -> Result[i64]",
          "(The struct Transfer is part of the program; include it in your answer.) " + dta.format(e="Err"),
          "\n  ".join(ta_aimy(i, *c) for i, c in enumerate(ta))),
    py=("from dataclasses import dataclass\n\n@dataclass\nclass Transfer:\n    src: int\n    dst: int\n    amt: int\n\n"
        "def transfer_all(bal: list[int], ts: list[Transfer]) -> int",
        "(The class Transfer is part of the program; include it in your answer.) " + dta.format(e="raise ValueError"),
        "\n".join(ta_py(*c) for c in ta)),
    rs=("#[derive(Debug, Clone, Copy, PartialEq)]\nstruct Transfer { src: i64, dst: i64, amt: i64 }\n\n"
        "fn transfer_all(bal: &mut [i64], ts: &[Transfer]) -> Result<i64, String>",
        "(The struct Transfer is part of the program; include it in your answer.) " + dta.format(e="Err"),
        "\n".join(ta_rs(i, *c) for i, c in enumerate(ta))),
)

d = ("The mean of xs rounded toward zero, {e}(\"empty\") for an empty input. Must be exact for any i64 values, "
     "even when their sum does not fit in i64 (the mean always does). len(xs) stays below 10^6.")
av = [("[1, 2]", "1"), ("[-1, -2]", "-1"), ("[7, -2]", "2"), ("[-7, 2]", "-2"), (f"[{MAX}, {MAX}, {MAX}]", MAX),
      (f"[{MIN}, {MIN}]", MIN), (f"[{MAX}, {MIN}]", "0"), (f"[{MAX}, {MAX}, -{MAX}]", "3074457345618258602"),
      (f"[{MIN}, {MIN}, 1]", "-6148914691236517205")]
T["avg_i64"] = dict(
    aimy=("fn avg_i64(xs: [i64]) -> Result[i64]", d.format(e="Err"),
          "let e: [i64] = []\n  avg_i64(e) == Err(\"empty\")\n  " + "\n  ".join(f"avg_i64({x}) == Ok({r})" for x, r in av)),
    py=("def avg_i64(xs: list[int]) -> int", d.format(e="raise ValueError"),
        "err(lambda: avg_i64([]), \"empty\")\n" + "\n".join(f"assert avg_i64({x}) == {r}" for x, r in av)),
    rs=("fn avg_i64(xs: &[i64]) -> Result<i64, String>", d.format(e="Err"),
        "assert_eq!(avg_i64(&[]), Err(\"empty\".to_string()));\n" + "\n".join(f"assert_eq!(avg_i64(&{x}), Ok({r}));" for x, r in av)),
)

d = ("Histogram with n bins of equal width w = (hi - lo) / n: bin i counts the values v with "
     "lo + i*w <= v < lo + (i+1)*w. Values outside [lo, hi) are ignored. Return the n counts. "
     "Precondition: n >= 1, lo < hi, (hi - lo) divisible by n, |lo| and |hi| below 10^15.")
hs = [("[0, 1, 2, 3, 9, 10, -1]", "0", "10", "5", "[2, 2, 0, 0, 1]"),
      ("[-10, -6, -5, -1, 0, 5]", "-10", "0", "2", "[2, 2]"),
      ("[]", "0", "4", "2", "[0, 0]"), ("[-1, -2, -3, 3]", "0", "3", "3", "[0, 0, 0]"),
      ("[-7, -4, -3, 2]", "-6", "3", "3", "[1, 1, 1]")]
T["hist"] = dict(
    aimy=("fn hist(xs: [i64], lo: i64, hi: i64, n: i64) -> [i64]\n  requires n >= 1 and lo < hi", d,
          "\n  ".join((f"let h{i}: [i64] = []\n  same(hist(h{i}, {lo}, {hi}, {n}), {r})" if x == "[]"
                       else f"same(hist({x}, {lo}, {hi}, {n}), {r})") for i, (x, lo, hi, n, r) in enumerate(hs))),
    py=("def hist(xs: list[int], lo: int, hi: int, n: int) -> list[int]", d,
        "\n".join(f"assert hist({x}, {lo}, {hi}, {n}) == {r}" for x, lo, hi, n, r in hs)),
    rs=("fn hist(xs: &[i64], lo: i64, hi: i64, n: i64) -> Vec<i64>", d,
        "\n".join(f"assert_eq!(hist(&{x}, {lo}, {hi}, {n}), vec!{r});" if x != "[]" else
                  f"assert_eq!(hist(&[], {lo}, {hi}, {n}), vec!{r});" for x, lo, hi, n, r in hs)),
)

# Terse variant: the same tasks and hidden tests, but the statement keeps only what
# defines the function (result, error messages and their order, preconditions) and drops
# every sentence that points at an edge case (i64 range, negative k, src == dst, ...).
# Written to tasks/<name>_terse, listed in eval/hard-terse.txt.
PRE = {"aimy": "", "py": " Precondition: {}.", "rs": " Precondition: {}."}
TERSE = {
    "median": ("The median of xs.", "xs is not empty"),
    "mid": ("The average of a and b, rounded toward zero.", None),
    "mul_mod": ("(a * b) mod m.", "m >= 1, 0 <= a < m, 0 <= b < m"),
    "identity": ("The n x n identity matrix as a list of rows.", "n >= 0"),
    "local_peaks": ("Count the elements that are strictly greater than each of their neighbors.", None),
    "rotate": ("Rotate xs right by k places in place (negative k rotates left).", None),
    "transfer": ("Move amt from bal[src] to bal[dst] and return the new balance of bal[src]. Errors, checked in "
                 "this order: {e}(\"bad account\") if src or dst is not an account; {e}(\"bad amount\") if amt <= 0; "
                 "{e}(\"insufficient funds\") if bal[src] < amt.", None),
    "transfer_all": ("Apply the transfers in order as one transaction and return how many were applied. Each moves amt "
                     "from bal[src] to bal[dst]. Errors, checked in this order for each transfer: {e}(\"bad account\") "
                     "if src or dst is not an account; {e}(\"bad amount\") if amt <= 0; {e}(\"insufficient funds\") "
                     "if bal[src] < amt. On an error the result is the first error.", None),
    "avg_i64": ("The mean of xs rounded toward zero; {e}(\"empty\") for an empty input.", None),
    "hist": ("Histogram of xs over [lo, hi) with n bins of equal width; return the n counts.",
             "n >= 1, lo < hi, hi - lo divisible by n"),
}
ERRW = {"aimy": "Err", "py": "raise ValueError", "rs": "Err"}
STRUCT_NOTE = {"aimy": "(The struct Transfer is part of the program; include it in your answer.) ",
               "py": "(The class Transfer is part of the program; include it in your answer.) ",
               "rs": "(The struct Transfer is part of the program; include it in your answer.) "}


def terse(name, langs):
    text, pre = TERSE[name]
    out = {}
    for lang, (sig, _, tests) in langs.items():
        d = text.format(e=ERRW[lang]) + (PRE[lang].format(pre) if pre else "")
        if name == "transfer_all":
            d = STRUCT_NOTE[lang] + d
        out[lang] = (sig, d, tests)
    return out


ALL = dict(T)
ALL.update({n + "_terse": terse(n, langs) for n, langs in T.items()})

root = pathlib.Path(__file__).parent
for name, langs in ALL.items():
    tname = name.removesuffix("_terse")
    out = root / "tasks" / name
    out.mkdir(exist_ok=True)
    sig, desc, tests = langs["aimy"]
    (out / "task.md").write_text(f"Write this aimy definition (name and signature exactly):\n\n```\n{sig}\n```\n\n{desc}\n")
    helpers = (SAME if "same(" in tests or "same2(" in tests else "") + (SAME2 if "same2(" in tests else "")
    (out / "tests.aim").write_text(helpers + f"test ref_{tname} {{\n  {tests}\n}} end ref_{tname}\n")
    sig, desc, tests = langs["py"]
    (out / "task.py.md").write_text(f"Write this Python 3.12 definition (name and signature exactly):\n\n"
                                    f"```python\n{sig}\n```\n\n{desc}\n")
    body = "\n".join("    " + l for l in tests.splitlines())
    (out / "tests.py").write_text((ERR if "err(" in tests else "") + f"def test_ref_{tname}():\n{body}\n")
    sig, desc, tests = langs["rs"]
    (out / "task.rs.md").write_text(f"Write this Rust (edition 2021, std only) definition (name and signature exactly):\n\n"
                                    f"```rust\n{sig}\n```\n\n{desc}\n")
    body = "\n".join("    " + l for l in tests.splitlines())
    (out / "tests.rs").write_text(f"#[test]\nfn test_ref_{tname}() {{\n{body}\n}}\n")
(root / "hard.txt").write_text("\n".join(T) + "\n")
(root / "hard-terse.txt").write_text("\n".join(n + "_terse" for n in T) + "\n")
