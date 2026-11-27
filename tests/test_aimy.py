import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def aimy(*args: str, src: str | None = None, tmp_path: Path | None = None) -> subprocess.CompletedProcess:
    argv = list(args)
    if src is not None:
        assert tmp_path is not None
        f = tmp_path / "t.aim"
        f.write_text(src)
        argv.insert(1, str(f))
    return subprocess.run([sys.executable, "-m", "aimy.cli", *argv], capture_output=True, text=True, cwd=ROOT)


def codes(src: str, tmp_path: Path) -> list[str]:
    r = aimy("check", src=src, tmp_path=tmp_path)
    return [json.loads(l)["code"] for l in r.stdout.splitlines() if '"code"' in l]


@pytest.mark.parametrize("name", ["fib", "sieve", "nbody", "shapes"])
def test_examples_pass_their_tests(name):
    r = aimy("test", f"examples/{name}.aim")
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout.splitlines()[-1])["summary"]["failed"] == 0


def test_run_fib():
    r = aimy("run", "examples/fib.aim", "20")
    assert r.stdout == "fib 20 = 6765\n"


def test_nbody_matches_reference():
    r = aimy("run", "examples/nbody.aim", "1000")
    assert r.stdout.split() == ["-0.16907516382852447", "-0.169087605234606"]


MAIN = "fn main() ! io {{\n{body}\n}} end main\n"


@pytest.mark.parametrize("body,code", [
    ("  let x = 1\n  let x = 2\n  print(x)", "E201"),           # shadowing
    ("  let x = 1\n  x = 2\n  print(x)", "E402"),               # immutable
    ("  let a = [1]\n  let b = a\n  print(len(b))", "E404"),    # silent alias
    ("  print(1 + 2.0)", "E513"),                               # no implicit conversion
    ("  prnt(1)", "E601"),                                      # unknown fn
    ("  let xs: [i64] = []\n  push(xs, 1)\n  print(len(xs))", "E603"),  # mut not marked
    ("  1 + 2", "E307"),                                        # unused value
])
def test_rules(body, code, tmp_path):
    assert code in codes(MAIN.format(body=body), tmp_path)


def test_effects_and_returns(tmp_path):
    src = "fn f() -> i64 {\n  print(1)\n} end f\n"
    assert {"E605", "E301"} <= set(codes(src, tmp_path))


def test_nesting_limit(tmp_path):
    src = ("fn f(n: i64) {\n  if n > 0 {\n    if n > 1 {\n      if n > 2 {\n"
           "        if n > 3 { assert(false) }\n      }\n    }\n  }\n} end f\n")
    assert "E302" in codes(src, tmp_path)


def test_end_label_mismatch(tmp_path):
    assert codes("fn f() {\n} end g\n", tmp_path) == ["E002"]


def test_typo_hint(tmp_path):
    src = "fn total() -> i64 { ret 1 } end total\n" + MAIN.format(body="  print(totl())")
    r = aimy("check", src=src, tmp_path=tmp_path)
    d = json.loads(r.stdout.splitlines()[0])
    assert d["hint"] == "did you mean 'total'?"


@pytest.mark.parametrize("body,kind", [
    ("  let xs = [1, 2]\n  print(xs[arg(0)])", "index_out_of_bounds"),
    ("  let mut x = 9223372036854775807\n  x += arg(0)\n  print(x)", "overflow"),
    ("  print(10 / (arg(0) - 5))", "div_by_zero"),
])
def test_runtime_errors(body, kind, tmp_path):
    r = aimy("run", "5", src=MAIN.format(body=body), tmp_path=tmp_path)
    assert r.returncode == 101
    assert json.loads(r.stderr.strip().splitlines()[-1])["kind"] == kind
    assert r.stdout == ""


def test_contract(tmp_path):
    src = "fn f(n: i64) -> i64\n  requires n > 0\n  ensures result > n\n{ ret n } end f\n" + \
          MAIN.format(body="  print(f(arg(0)))")
    assert json.loads(aimy("run", "0", src=src, tmp_path=tmp_path).stderr)["kind"] == "requires"
    assert json.loads(aimy("run", "3", src=src, tmp_path=tmp_path).stderr)["kind"] == "ensures"


def test_failed_assertion_shows_values(tmp_path):
    r = aimy("test", src="test t {\n  1 + 1 == 3\n} end t\n", tmp_path=tmp_path)
    res = json.loads(r.stdout.splitlines()[0])
    assert (res["status"], res["left"], res["right"]) == ("fail", "2", "3")


def test_copy_is_independent(tmp_path):
    body = "  let mut a = [[1, 2], [3]]\n  let mut b = copy(a)\n  b[0][0] = 9\n  push(mut b, [4])\n  print(a[0][0], len(a), b[0][0], len(b))"
    r = aimy("run", src=MAIN.format(body=body), tmp_path=tmp_path)
    assert r.stdout == "1 2 9 3\n"


def test_io_argument_order(tmp_path):
    src = ("fn say(n: i64) -> i64 ! io {\n  print(n)\n  ret n\n} end say\n"
           "fn add(a: i64, b: i64) -> i64 { ret a + b } end add\n"
           + MAIN.format(body="  print(add(say(1), say(2)))"))
    assert aimy("run", src=src, tmp_path=tmp_path).stdout == "1\n2\n3\n"


def test_return_local_array_moves(tmp_path):
    ok = "fn f() -> [i64] {\n  let mut o: [i64] = []\n  push(mut o, 1)\n  ret o\n} end f\n"
    bad = "fn g(p: [i64]) -> [i64] {\n  ret p\n} end g\n"
    for src, code in ((ok, None), (bad, "E404")):
        f = tmp_path / "t.aim"
        f.write_text(src)
        r = subprocess.run([sys.executable, "-m", "aimy.cli", "check", str(f)], capture_output=True, text=True)
        assert (code in r.stdout) if code else (r.returncode == 0), r.stdout


# ---------- v0.2: enums, match, Option/Result, generics ----------

ENUM = "enum Shape { Circle(f64), Rect(f64, f64), Empty } end Shape\n"


def fn_src(body: str) -> str:
    return ENUM + body + "\n"


@pytest.mark.parametrize("src,code", [
    ("fn f(s: Shape) -> i64 {\n  match s {\n    Shape.Circle(_) => ret 1\n  }\n} end f", "E710"),   # not exhaustive
    ("fn f(s: Shape) -> i64 {\n  match s {\n    Shape.Rect(w) => ret 1\n    _ => ret 2\n  }\n} end f", "E704"),
    ("fn f(s: Shape) -> i64 {\n  match s {\n    Shape.Empty => ret 0\n    Shape.Empty => ret 0\n    _ => ret 1\n  }\n} end f", "E709"),
    ("fn f(o: Option[i64]) -> i64 {\n  match o {\n    Some(x) => ret x\n    None => ret 0\n    _ => ret 1\n  }\n} end f", "E708"),
    ("fn f(x: i64) -> i64 {\n  match x {\n    _ => ret 0\n  }\n} end f", "E707"),
    ("fn f() -> Shape { ret Shape.Square } end f", "E703"),
    ("fn f() -> i64 {\n  let _ = None\n  ret 1\n} end f", "E701"),
    ("fn g() -> Result[i64] { ret Ok(1) } end g\nfn f() {\n  g()\n} end f", "E711"),          # unhandled Result
    ("fn g() -> Result[i64] { ret Ok(1) } end g\nfn f() {\n  let _ = g()\n} end f", "E711"),
    ("fn g() -> Result[i64] { ret Ok(1) } end g\nfn f() -> i64 { ret g()? } end f", "E706"),     # ? needs Result fn
    ("enum L { Cons(i64, L), Nil } end L", "E110"),                                               # recursive by value
    ("fn f[T](a: T, b: T) -> bool { ret a == b } end f", "E514"),
    ("fn f[T](x: T, n: i64) -> i64 {\n  if n == 0 { ret 0 }\n  ret f([copy(x)], n - 1)\n} end f", "E714"),
    ("fn f(Xs: i64) -> i64 { ret Xs } end f", "E204"),                                            # lowercase names
    ("fn f(a: [i64]) -> Option[[i64]] { ret Some(a) } end f", "E404"),                            # alias via payload
])
def test_v02_rules(src, code, tmp_path):
    assert code in codes(fn_src(src), tmp_path)


@pytest.mark.parametrize("src", [
    "fn f() -> Shape { ret Shape::Empty } end f",
    "fn f(s: Shape) -> i64 {\n  match s {\n    Circle(r) => ret 1\n    _ => ret 2\n  }\n} end f",
    "fn f() -> Result[i64, str] { ret Ok(1) } end f",
])
def test_v02_rust_habits_get_hints(src, tmp_path):
    r = aimy("check", src=fn_src(src), tmp_path=tmp_path)
    d = json.loads(r.stdout.splitlines()[0])
    assert d["code"] == "E002" and d.get("hint")


def test_ret_moves_local_into_variant(tmp_path):
    src = "fn f() -> Option[[i64]] {\n  let a = [1]\n  ret Some(a)\n} end f\n" \
          "fn g() -> [[i64]] {\n  let a = [1]\n  ret [a, a]\n} end g\n"
    assert codes(src, tmp_path) == ["E404"]  # only the second use of 'a' in g


def test_match_break_continue_and_try(tmp_path):
    src = ("enum Cmd { Stop, Add(i64), Skip } end Cmd\n"
           "fn run(cs: [Cmd]) -> i64 {\n  let mut n = 0\n  for i in 0..len(cs) {\n    match cs[i] {\n"
           "      Cmd.Stop => break\n      Cmd.Add(v) => n += v\n      Cmd.Skip => continue\n    }\n"
           "    n += 100\n  }\n  ret n\n} end run\n"
           "fn pos(x: i64) -> Result[i64] {\n  if x < 0 { ret Err(\"neg\") }\n  ret Ok(x)\n} end pos\n"
           "fn add(a: i64, b: i64) -> Result[i64] { ret Ok(pos(a)? + pos(b)?) } end add\n"
           + MAIN.format(body="  print(run([Cmd.Add(1), Cmd.Skip, Cmd.Add(2), Cmd.Stop, Cmd.Add(50)]))\n"
                              "  match add(arg(0), arg(1)) {\n    Ok(v) => print(v)\n    Err(m) => print(m)\n  }"))
    assert aimy("run", "3", "4", src=src, tmp_path=tmp_path).stdout == "203\n7\n"
    assert aimy("run", "3", "-1", src=src, tmp_path=tmp_path).stdout == "203\nneg\n"


def test_failed_assertion_shows_enum_values(tmp_path):
    src = "test t {\n  Some(\"a\") == Some(\"b\")\n} end t\n"
    res = json.loads(aimy("test", src=src, tmp_path=tmp_path).stdout.splitlines()[0])
    assert (res["left"], res["right"]) == ('Some("a")', 'Some("b")')


def test_generic_instances(tmp_path):
    src = ("fn last[T](xs: [T]) -> Option[T] {\n  if len(xs) == 0 { ret None }\n  ret Some(copy(xs[len(xs) - 1]))\n} end last\n"
           "fn wrap[T](x: T) -> [T] { ret [copy(x)] } end wrap\n"
           "test t {\n  last([1, 2]) == Some(2)\n  last([\"x\"]) == Some(\"x\")\n"
           "  let e: [f64] = []\n  last(e) == None\n  len(wrap(wrap(3))[0]) == 1\n} end t\n")
    r = aimy("test", src=src, tmp_path=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_e404_type_param_message(tmp_path):
    f = tmp_path / "t.aim"
    f.write_text("fn f[T](d: T) -> T { ret d } end f\n")
    r = subprocess.run([sys.executable, "-m", "aimy.cli", "check", str(f)], capture_output=True, text=True)
    assert "E404" in r.stdout and "type parameter can be an array" in r.stdout, r.stdout
