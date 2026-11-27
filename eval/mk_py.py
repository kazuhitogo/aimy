"""Generate the Python baseline: tasks/<name>/task.py.md and tests.py, one per aimy task.

Same problems as mk.py. aimy Result errors become `raise ValueError(msg)`, Option becomes
`None`, enums become Enum classes or dataclasses given in the task, contracts become stated
preconditions. Python ints do not overflow, so i64 limits are stated where a task depends on them.
"""
import pathlib

ENUM = "from enum import Enum\n\n"
DC = "from dataclasses import dataclass\n\n"
T = [
("sum_to", "def sum_to(n: int) -> int", "Sum of integers 1..=n. n>=0; sum_to(0)==0.",
 "assert sum_to(0) == 0\nassert sum_to(1) == 1\nassert sum_to(100) == 5050"),
("is_prime", "def is_prime(n: int) -> bool", "True if n is prime. n can be any int (<2 is not prime).",
 "assert is_prime(-5) is False\nassert is_prime(1) is False\nassert is_prime(2)\nassert is_prime(97)\n"
 "assert is_prime(91) is False\nassert is_prime(7919)"),
("gcd", "def gcd(a: int, b: int) -> int", "Greatest common divisor of a,b >= 0. gcd(x,0)==x.",
 "assert gcd(12, 18) == 6\nassert gcd(7, 0) == 7\nassert gcd(0, 0) == 0\nassert gcd(17, 13) == 1"),
("fib", "def fib(n: int) -> int", "n-th Fibonacci number, fib(0)=0, fib(1)=1, iterative. n in 0..=90.",
 "assert fib(0) == 0\nassert fib(1) == 1\nassert fib(10) == 55\nassert fib(90) == 2880067194370816120"),
("pow_mod", "def pow_mod(b: int, e: int, m: int) -> int", "b^e mod m for 0<=b, 0<=e, 1<=m<=1000000000.",
 "assert pow_mod(2, 10, 1000) == 24\nassert pow_mod(3, 0, 7) == 1\nassert pow_mod(2, 100, 1000000007) == 976371285\n"
 "assert pow_mod(999999999, 999999999, 1000000000) == 999999999"),
("sum_array", "def sum_array(xs: list[int]) -> int", "Sum of all elements; empty gives 0.",
 "assert sum_array([]) == 0\nassert sum_array([1, 2, 3]) == 6\nassert sum_array([-5, 5, 7]) == 7"),
("max_array", "def max_array(xs: list[int]) -> int", "Largest element. Precondition: len(xs) > 0.",
 "assert max_array([3]) == 3\nassert max_array([1, 9, 4]) == 9\nassert max_array([-3, -1, -2]) == -1"),
("reverse", "def reverse(xs: list[int]) -> list[int]", "A new list with elements in reverse order. Do not modify xs.",
 "assert reverse([]) == []\na = [1, 2, 3]\nassert reverse(a) == [3, 2, 1]\nassert a == [1, 2, 3]"),
("count_evens", "def count_evens(xs: list[int]) -> int", "Count of even elements (negatives included).",
 "assert count_evens([]) == 0\nassert count_evens([1, 2, 4, -6, 7]) == 3"),
("prefix_sums", "def prefix_sums(xs: list[int]) -> list[int]", "List p of same length where p[i] = xs[0]+...+xs[i].",
 "assert prefix_sums([]) == []\nassert prefix_sums([1, 2, 3, 4]) == [1, 3, 6, 10]"),
("sort", "def sort(xs: list[int]) -> None", "Sort xs ascending in place.",
 "a = [3, 1, 2]\nsort(a)\nassert a == [1, 2, 3]\nb = []\nsort(b)\nassert b == []\n"
 "c = [5, 5, -1, 9, 0]\nsort(c)\nassert c == [-1, 0, 5, 5, 9]"),
("binary_search", "def binary_search(xs: list[int], t: int) -> int", "xs sorted ascending. Index of t, or -1 if absent.",
 "assert binary_search([], 1) == -1\nassert binary_search([1, 3, 5, 7], 5) == 2\n"
 "assert binary_search([1, 3, 5, 7], 1) == 0\nassert binary_search([1, 3, 5, 7], 4) == -1"),
("dot", "def dot(a: list[float], b: list[float]) -> float", "Dot product; empty gives 0.0. Precondition: len(a) == len(b).",
 "assert dot([], []) == 0.0\nassert dot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 32.0"),
("mean", "def mean(xs: list[float]) -> float", "Arithmetic mean. Precondition: len(xs) > 0.",
 "assert mean([2.0, 4.0]) == 3.0\nassert mean([5.0]) == 5.0"),
("dist2", DC + "@dataclass\nclass Point:\n    x: int\n    y: int\n\ndef dist2(a: Point, b: Point) -> int",
 "(The class Point is part of the program; include it in your answer.) Squared Euclidean distance.",
 "assert dist2(Point(0, 0), Point(3, 4)) == 25\nassert dist2(Point(-1, -1), Point(-1, -1)) == 0"),
("rect_area", DC + "@dataclass\nclass Rect:\n    w: int\n    h: int\n\ndef total_area(rs: list[Rect]) -> int",
 "(The class Rect is part of the program; include it in your answer.) Sum of w*h over all rectangles.",
 "assert total_area([]) == 0\nassert total_area([Rect(2, 3), Rect(4, 5)]) == 26"),
("collatz", "def collatz_steps(n: int) -> int", "Steps to reach 1: halve if even, else 3n+1. Precondition: n >= 1.",
 "assert collatz_steps(1) == 0\nassert collatz_steps(6) == 8\nassert collatz_steps(27) == 111"),
("digit_sum", "def digit_sum(n: int) -> int", "Sum of decimal digits. Precondition: n >= 0.",
 "assert digit_sum(0) == 0\nassert digit_sum(12345) == 15\nassert digit_sum(1000) == 1"),
("count_unique", "def count_unique(xs: list[int]) -> int", "Number of distinct values in xs (unsorted, any order). Do not modify xs.",
 "assert count_unique([]) == 0\nassert count_unique([1, 1, 1]) == 1\na = [3, 1, 3, 2, 1]\n"
 "assert count_unique(a) == 3\nassert a == [3, 1, 3, 2, 1]"),
# v0.2 counterparts: errors are ValueError, missing values are None
("safe_div", "def safe_div(a: int, b: int) -> int",
 "Integer division truncating toward zero, on 64-bit signed values. Raise ValueError(\"division by zero\") if b == 0; "
 "raise ValueError(\"overflow\") if a is the smallest i64 (-2**63) and b == -1.",
 "assert safe_div(7, 2) == 3\nassert safe_div(-7, 2) == -3\nerr(lambda: safe_div(1, 0), \"division by zero\")\n"
 "err(lambda: safe_div(-9223372036854775808, -1), \"overflow\")\n"
 "assert safe_div(-9223372036854775808, 1) == -9223372036854775808"),
("find_index", "def find_index(xs: list[int], t: int) -> int | None", "Index of the first element equal to t, or None.",
 "assert find_index([], 1) is None\nassert find_index([4, 7, 7], 7) == 1\nassert find_index([4, 7], 5) is None"),
("min_pos", "def min_pos(xs: list[int]) -> int | None", "Smallest element that is > 0, or None if there is none.",
 "assert min_pos([]) is None\nassert min_pos([-1, 0]) is None\nassert min_pos([5, -3, 2, 9]) == 2"),
("mean_checked", "def mean_checked(xs: list[float]) -> float", "Arithmetic mean; raise ValueError(\"empty\") for an empty list.",
 "err(lambda: mean_checked([]), \"empty\")\nassert mean_checked([1.0, 2.0]) == 1.5"),
("checked_sum", "def checked_sum(xs: list[int]) -> int",
 "Sum of the elements; raise ValueError(\"overflow\") if the sum (or any partial sum, left to right) "
 "is outside the i64 range -2**63 ..= 2**63-1.",
 "assert checked_sum([]) == 0\nassert checked_sum([1, 2, 3]) == 6\n"
 "err(lambda: checked_sum([9223372036854775807, 1]), \"overflow\")\n"
 "err(lambda: checked_sum([-9223372036854775807, -1, -1]), \"overflow\")\n"
 "assert checked_sum([9223372036854775807, -1, 1]) == 9223372036854775807"),
("classify", ENUM + "class Tri(Enum):\n    EQUILATERAL = 1\n    ISOSCELES = 2\n    SCALENE = 3\n    INVALID = 4\n\n"
 "def classify(a: int, b: int, c: int) -> Tri",
 "(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths "
 "(each below 1000000000). INVALID if any side <= 0 or the two shorter sides sum to <= the longest.",
 "assert classify(3, 3, 3) == Tri.EQUILATERAL\nassert classify(3, 3, 5) == Tri.ISOSCELES\n"
 "assert classify(5, 3, 3) == Tri.ISOSCELES\nassert classify(3, 4, 5) == Tri.SCALENE\n"
 "assert classify(1, 2, 3) == Tri.INVALID\nassert classify(0, 1, 1) == Tri.INVALID"),
("light", ENUM + "class Light(Enum):\n    RED = 1\n    GREEN = 2\n    YELLOW = 3\n\ndef after(l: Light, n: int) -> Light",
 "(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle "
 "RED -> GREEN -> YELLOW -> RED. Precondition: n >= 0. n can be up to 10**18.",
 "assert after(Light.RED, 0) == Light.RED\nassert after(Light.RED, 1) == Light.GREEN\n"
 "assert after(Light.GREEN, 2) == Light.RED\nassert after(Light.YELLOW, 1000000000000000000) == Light.RED"),
("bank", DC + "@dataclass\nclass Deposit:\n    amount: int\n\n@dataclass\nclass Withdraw:\n    amount: int\n\n"
 "Tx = Deposit | Withdraw\n\ndef apply(balance: int, txs: list[Tx]) -> int",
 "(The classes Deposit, Withdraw and the alias Tx are part of the program; include them in your answer.) "
 "Apply transactions in order, return the final balance. Raise ValueError(\"invalid amount\") for an amount <= 0; "
 "raise ValueError(\"insufficient funds\") if a withdrawal exceeds the current balance. Stop at the first error.",
 "assert apply(10, []) == 10\nassert apply(0, [Deposit(5), Withdraw(3)]) == 2\n"
 "err(lambda: apply(0, [Withdraw(1), Deposit(0)]), \"insufficient funds\")\n"
 "err(lambda: apply(5, [Deposit(0)]), \"invalid amount\")"),
("stack_calc", DC + "@dataclass\nclass Push:\n    value: int\n\n@dataclass\nclass Add:\n    pass\n\n"
 "@dataclass\nclass Mul:\n    pass\n\n@dataclass\nclass Neg:\n    pass\n\nOp = Push | Add | Mul | Neg\n\n"
 "def calc(ops: list[Op]) -> int",
 "(The classes Push, Add, Mul, Neg and the alias Op are part of the program; include them in your answer.) "
 "Run a stack machine: Push puts a value; Add and Mul pop two values and push the result; Neg negates the top. "
 "Raise ValueError(\"underflow\") if an op lacks operands; at the end return the top of the stack, "
 "or raise ValueError(\"empty\") if the stack is empty.",
 "err(lambda: calc([]), \"empty\")\nassert calc([Push(2), Push(3), Add(), Push(4), Mul()]) == 20\n"
 "assert calc([Push(2), Neg()]) == -2\nerr(lambda: calc([Push(1), Add()]), \"underflow\")\n"
 "err(lambda: calc([Neg()]), \"underflow\")"),
("last_or", "def last_or[T](xs: list[T], d: T) -> T", "Generic: the last element of xs, or d if xs is empty.",
 "assert last_or([1, 2, 3], 0) == 3\nassert last_or([], 7) == 7\nassert last_or([\"a\", \"b\"], \"z\") == \"b\""),
]
HELP = '''def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

'''

root = pathlib.Path(__file__).parent / "tasks"
for name, sig, desc, tests in T:
    d = root / name
    assert d.is_dir(), name
    (d / "task.py.md").write_text(f"Write this Python 3.12 definition (name and signature exactly):\n\n"
                                  f"```python\n{sig}\n```\n\n{desc}\n")
    body = "\n".join("    " + l for l in tests.splitlines())
    (d / "tests.py").write_text((HELP if "err(" in tests else "") + f"def test_ref_{name}():\n{body}\n")
