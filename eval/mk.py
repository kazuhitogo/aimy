import pathlib
T = [
("sum_to","fn sum_to(n: i64) -> i64","Sum of integers 1..=n. n>=0; sum_to(0)==0.","sum_to(0) == 0\n  sum_to(1) == 1\n  sum_to(100) == 5050"),
("is_prime","fn is_prime(n: i64) -> bool","True if n is prime. n can be any i64 (<2 is not prime).","is_prime(-5) == false\n  is_prime(1) == false\n  is_prime(2)\n  is_prime(97)\n  is_prime(91) == false\n  is_prime(7919)"),
("gcd","fn gcd(a: i64, b: i64) -> i64","Greatest common divisor of a,b >= 0. gcd(x,0)==x.","gcd(12, 18) == 6\n  gcd(7, 0) == 7\n  gcd(0, 0) == 0\n  gcd(17, 13) == 1"),
("fib","fn fib(n: i64) -> i64","n-th Fibonacci number, fib(0)=0, fib(1)=1, iterative. n in 0..=90.","fib(0) == 0\n  fib(1) == 1\n  fib(10) == 55\n  fib(90) == 2880067194370816120"),
("pow_mod","fn pow_mod(b: i64, e: i64, m: i64) -> i64","b^e mod m for 0<=b, 0<=e, 1<=m<=1000000000. Must not overflow i64.","pow_mod(2, 10, 1000) == 24\n  pow_mod(3, 0, 7) == 1\n  pow_mod(2, 100, 1000000007) == 976371285\n  pow_mod(999999999, 999999999, 1000000000) == 999999999"),
("sum_array","fn sum_array(xs: [i64]) -> i64","Sum of all elements; empty gives 0.","sum_array([]) == 0\n  sum_array([1, 2, 3]) == 6\n  sum_array([-5, 5, 7]) == 7"),
("max_array","fn max_array(xs: [i64]) -> i64\n  requires len(xs) > 0","Largest element.","max_array([3]) == 3\n  max_array([1, 9, 4]) == 9\n  max_array([-3, -1, -2]) == -1"),
("reverse","fn reverse(xs: [i64]) -> [i64]","A new array with elements in reverse order.","same(reverse([]), [])\n  same(reverse([1, 2, 3]), [3, 2, 1])"),
("count_evens","fn count_evens(xs: [i64]) -> i64","Count of even elements (negatives included).","count_evens([]) == 0\n  count_evens([1, 2, 4, -6, 7]) == 3"),
("prefix_sums","fn prefix_sums(xs: [i64]) -> [i64]","Array p of same length where p[i] = xs[0]+...+xs[i].","same(prefix_sums([]), [])\n  same(prefix_sums([1, 2, 3, 4]), [1, 3, 6, 10])"),
("sort","fn sort(mut xs: [i64])","Sort xs ascending in place.","let mut a: [i64] = [3, 1, 2]\n  sort(mut a)\n  same(a, [1, 2, 3])\n  let mut b: [i64] = []\n  sort(mut b)\n  same(b, [])\n  let mut c: [i64] = [5, 5, -1, 9, 0]\n  sort(mut c)\n  same(c, [-1, 0, 5, 5, 9])"),
("binary_search","fn binary_search(xs: [i64], t: i64) -> i64","xs sorted ascending. Index of t, or -1 if absent.","binary_search([], 1) == -1\n  binary_search([1, 3, 5, 7], 5) == 2\n  binary_search([1, 3, 5, 7], 1) == 0\n  binary_search([1, 3, 5, 7], 4) == -1"),
("dot","fn dot(a: [f64], b: [f64]) -> f64\n  requires len(a) == len(b)","Dot product; empty gives 0.0.","dot([], []) == 0.0\n  dot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 32.0"),
("mean","fn mean(xs: [f64]) -> f64\n  requires len(xs) > 0","Arithmetic mean.","mean([2.0, 4.0]) == 3.0\n  mean([5.0]) == 5.0"),
("dist2","struct Point { x: i64, y: i64 } end Point\n\nfn dist2(a: Point, b: Point) -> i64","(The struct Point is part of the program; include it in your answer.) Squared Euclidean distance.","dist2(Point{x: 0, y: 0}, Point{x: 3, y: 4}) == 25\n  dist2(Point{x: -1, y: -1}, Point{x: -1, y: -1}) == 0"),
("rect_area","struct Rect { w: i64, h: i64 } end Rect\n\nfn total_area(rs: [Rect]) -> i64","(The struct Rect is part of the program; include it in your answer.) Sum of w*h over all rectangles.","total_area([]) == 0\n  total_area([Rect{w: 2, h: 3}, Rect{w: 4, h: 5}]) == 26"),
("collatz","fn collatz_steps(n: i64) -> i64\n  requires n >= 1","Steps to reach 1: halve if even, else 3n+1.","collatz_steps(1) == 0\n  collatz_steps(6) == 8\n  collatz_steps(27) == 111"),
("digit_sum","fn digit_sum(n: i64) -> i64\n  requires n >= 0","Sum of decimal digits.","digit_sum(0) == 0\n  digit_sum(12345) == 15\n  digit_sum(1000) == 1"),
("count_unique","fn count_unique(xs: [i64]) -> i64","Number of distinct values in xs (unsorted, any order). Do not modify xs.","count_unique([]) == 0\n  count_unique([1, 1, 1]) == 1\n  count_unique([3, 1, 3, 2, 1]) == 3"),
# v0.2: enums, match, Option/Result, generics
("safe_div","fn safe_div(a: i64, b: i64) -> Result[i64]","Err(\"division by zero\") if b == 0; Err(\"overflow\") if a is the smallest i64 and b == -1; otherwise Ok(a / b).","safe_div(7, 2) == Ok(3)\n  safe_div(-7, 2) == Ok(-3)\n  safe_div(1, 0) == Err(\"division by zero\")\n  safe_div(-9223372036854775808, -1) == Err(\"overflow\")\n  safe_div(-9223372036854775808, 1) == Ok(-9223372036854775808)"),
("find_index","fn find_index(xs: [i64], t: i64) -> Option[i64]","Index of the first element equal to t, or None.","find_index([], 1) == None\n  find_index([4, 7, 7], 7) == Some(1)\n  find_index([4, 7], 5) == None"),
("min_pos","fn min_pos(xs: [i64]) -> Option[i64]","Smallest element that is > 0, or None if there is none.","min_pos([]) == None\n  min_pos([-1, 0]) == None\n  min_pos([5, -3, 2, 9]) == Some(2)"),
("mean_checked","fn mean_checked(xs: [f64]) -> Result[f64]","Arithmetic mean; Err(\"empty\") for an empty array.","mean_checked([]) == Err(\"empty\")\n  mean_checked([1.0, 2.0]) == Ok(1.5)"),
("checked_sum","fn checked_sum(xs: [i64]) -> Result[i64]","Sum of the elements; Err(\"overflow\") if the sum (or any partial sum, left to right) does not fit in i64. Must not trap.","checked_sum([]) == Ok(0)\n  checked_sum([1, 2, 3]) == Ok(6)\n  checked_sum([9223372036854775807, 1]) == Err(\"overflow\")\n  checked_sum([-9223372036854775807, -1, -1]) == Err(\"overflow\")\n  checked_sum([9223372036854775807, -1, 1]) == Ok(9223372036854775807)"),
("classify","enum Tri { Equilateral, Isosceles, Scalene, Invalid } end Tri\n\nfn classify(a: i64, b: i64, c: i64) -> Tri","(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths (each below 1000000000). Invalid if any side <= 0 or the two shorter sides sum to <= the longest.","classify(3, 3, 3) == Tri.Equilateral\n  classify(3, 3, 5) == Tri.Isosceles\n  classify(5, 3, 3) == Tri.Isosceles\n  classify(3, 4, 5) == Tri.Scalene\n  classify(1, 2, 3) == Tri.Invalid\n  classify(0, 1, 1) == Tri.Invalid"),
("light","enum Light { Red, Green, Yellow } end Light\n\nfn after(l: Light, n: i64) -> Light\n  requires n >= 0","(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle Red -> Green -> Yellow -> Red. n can be up to 10^18.","after(Light.Red, 0) == Light.Red\n  after(Light.Red, 1) == Light.Green\n  after(Light.Green, 2) == Light.Red\n  after(Light.Yellow, 1000000000000000000) == Light.Red"),
("bank","enum Tx { Deposit(i64), Withdraw(i64) } end Tx\n\nfn apply(balance: i64, txs: [Tx]) -> Result[i64]","(The enum Tx is part of the program; include it in your answer.) Apply transactions in order, return the final balance. Err(\"invalid amount\") for an amount <= 0; Err(\"insufficient funds\") if a withdrawal exceeds the current balance. Stop at the first error. Amounts and balances stay below 10^15.","apply(10, []) == Ok(10)\n  apply(0, [Tx.Deposit(5), Tx.Withdraw(3)]) == Ok(2)\n  apply(0, [Tx.Withdraw(1), Tx.Deposit(0)]) == Err(\"insufficient funds\")\n  apply(5, [Tx.Deposit(0)]) == Err(\"invalid amount\")"),
("stack_calc","enum Op { Push(i64), Add, Mul, Neg } end Op\n\nfn calc(ops: [Op]) -> Result[i64]","(The enum Op is part of the program; include it in your answer.) Run a stack machine: Push puts a value; Add and Mul pop two values and push the result; Neg negates the top. Err(\"underflow\") if an op lacks operands; at the end return the top of the stack, or Err(\"empty\") if the stack is empty. Values stay small.","calc([]) == Err(\"empty\")\n  calc([Op.Push(2), Op.Push(3), Op.Add, Op.Push(4), Op.Mul]) == Ok(20)\n  calc([Op.Push(2), Op.Neg]) == Ok(-2)\n  calc([Op.Push(1), Op.Add]) == Err(\"underflow\")\n  calc([Op.Neg]) == Err(\"underflow\")"),
("last_or","fn last_or[T](xs: [T], d: T) -> T","Generic: the last element of xs, or d if xs is empty.","last_or([1, 2, 3], 0) == 3\n  let e: [i64] = []\n  last_or(e, 7) == 7\n  last_or([\"a\", \"b\"], \"z\") == \"b\""),
]
HELP = """fn same(a: [i64], b: [i64]) -> bool {
  if len(a) != len(b) { ret false }
  for i in 0..len(a) {
    if a[i] != b[i] { ret false }
  }
  ret true
} end same

"""
root = pathlib.Path(__file__).parent / "tasks"
for name, sig, desc, tests in T:
    d = root / name; d.mkdir(exist_ok=True)
    (d/"task.md").write_text(f"Write this aimy definition (name and signature exactly):\n\n```\n{sig}\n```\n\n{desc}\n")
    (d/"tests.aim").write_text((HELP if "same(" in tests else "") + f"test ref_{name} {{\n  {tests}\n}} end ref_{name}\n")
