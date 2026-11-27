"""Generate the Rust baseline: tasks/<name>/task.rs.md and tests.rs, one per aimy task.

Same problems as mk.py. aimy Result[T] becomes Result<T, String>, Option stays Option,
arrays are taken as slices, enums/structs are given in the task with derives the tests need,
contracts become stated preconditions. Judged with overflow checks on (like aimy).
"""
import pathlib

D = "#[derive(Debug, Clone, Copy, PartialEq)]\n"
T = [
("sum_to", "fn sum_to(n: i64) -> i64", "Sum of integers 1..=n. n>=0; sum_to(0)==0.",
 "assert_eq!(sum_to(0), 0);\nassert_eq!(sum_to(1), 1);\nassert_eq!(sum_to(100), 5050);"),
("is_prime", "fn is_prime(n: i64) -> bool", "True if n is prime. n can be any i64 (<2 is not prime).",
 "assert!(!is_prime(-5));\nassert!(!is_prime(1));\nassert!(is_prime(2));\nassert!(is_prime(97));\n"
 "assert!(!is_prime(91));\nassert!(is_prime(7919));"),
("gcd", "fn gcd(a: i64, b: i64) -> i64", "Greatest common divisor of a,b >= 0. gcd(x,0)==x.",
 "assert_eq!(gcd(12, 18), 6);\nassert_eq!(gcd(7, 0), 7);\nassert_eq!(gcd(0, 0), 0);\nassert_eq!(gcd(17, 13), 1);"),
("fib", "fn fib(n: i64) -> i64", "n-th Fibonacci number, fib(0)=0, fib(1)=1, iterative. n in 0..=90.",
 "assert_eq!(fib(0), 0);\nassert_eq!(fib(1), 1);\nassert_eq!(fib(10), 55);\nassert_eq!(fib(90), 2880067194370816120);"),
("pow_mod", "fn pow_mod(b: i64, e: i64, m: i64) -> i64",
 "b^e mod m for 0<=b, 0<=e, 1<=m<=1000000000. Must not overflow i64.",
 "assert_eq!(pow_mod(2, 10, 1000), 24);\nassert_eq!(pow_mod(3, 0, 7), 1);\n"
 "assert_eq!(pow_mod(2, 100, 1000000007), 976371285);\nassert_eq!(pow_mod(999999999, 999999999, 1000000000), 999999999);"),
("sum_array", "fn sum_array(xs: &[i64]) -> i64", "Sum of all elements; empty gives 0.",
 "assert_eq!(sum_array(&[]), 0);\nassert_eq!(sum_array(&[1, 2, 3]), 6);\nassert_eq!(sum_array(&[-5, 5, 7]), 7);"),
("max_array", "fn max_array(xs: &[i64]) -> i64", "Largest element. Precondition: xs.len() > 0.",
 "assert_eq!(max_array(&[3]), 3);\nassert_eq!(max_array(&[1, 9, 4]), 9);\nassert_eq!(max_array(&[-3, -1, -2]), -1);"),
("reverse", "fn reverse(xs: &[i64]) -> Vec<i64>", "A new vector with elements in reverse order.",
 "assert_eq!(reverse(&[]), Vec::<i64>::new());\nassert_eq!(reverse(&[1, 2, 3]), vec![3, 2, 1]);"),
("count_evens", "fn count_evens(xs: &[i64]) -> i64", "Count of even elements (negatives included).",
 "assert_eq!(count_evens(&[]), 0);\nassert_eq!(count_evens(&[1, 2, 4, -6, 7]), 3);"),
("prefix_sums", "fn prefix_sums(xs: &[i64]) -> Vec<i64>", "Vector p of same length where p[i] = xs[0]+...+xs[i].",
 "assert_eq!(prefix_sums(&[]), Vec::<i64>::new());\nassert_eq!(prefix_sums(&[1, 2, 3, 4]), vec![1, 3, 6, 10]);"),
("sort", "fn sort(xs: &mut [i64])", "Sort xs ascending in place.",
 "let mut a = vec![3, 1, 2];\nsort(&mut a);\nassert_eq!(a, vec![1, 2, 3]);\nlet mut b: Vec<i64> = vec![];\n"
 "sort(&mut b);\nassert_eq!(b, Vec::<i64>::new());\nlet mut c = vec![5, 5, -1, 9, 0];\nsort(&mut c);\n"
 "assert_eq!(c, vec![-1, 0, 5, 5, 9]);"),
("binary_search", "fn binary_search(xs: &[i64], t: i64) -> i64", "xs sorted ascending. Index of t, or -1 if absent.",
 "assert_eq!(binary_search(&[], 1), -1);\nassert_eq!(binary_search(&[1, 3, 5, 7], 5), 2);\n"
 "assert_eq!(binary_search(&[1, 3, 5, 7], 1), 0);\nassert_eq!(binary_search(&[1, 3, 5, 7], 4), -1);"),
("dot", "fn dot(a: &[f64], b: &[f64]) -> f64", "Dot product; empty gives 0.0. Precondition: a.len() == b.len().",
 "assert_eq!(dot(&[], &[]), 0.0);\nassert_eq!(dot(&[1.0, 2.0, 3.0], &[4.0, 5.0, 6.0]), 32.0);"),
("mean", "fn mean(xs: &[f64]) -> f64", "Arithmetic mean. Precondition: xs.len() > 0.",
 "assert_eq!(mean(&[2.0, 4.0]), 3.0);\nassert_eq!(mean(&[5.0]), 5.0);"),
("dist2", D + "struct Point { x: i64, y: i64 }\n\nfn dist2(a: Point, b: Point) -> i64",
 "(The struct Point is part of the program; include it in your answer.) Squared Euclidean distance.",
 "assert_eq!(dist2(Point { x: 0, y: 0 }, Point { x: 3, y: 4 }), 25);\n"
 "assert_eq!(dist2(Point { x: -1, y: -1 }, Point { x: -1, y: -1 }), 0);"),
("rect_area", D + "struct Rect { w: i64, h: i64 }\n\nfn total_area(rs: &[Rect]) -> i64",
 "(The struct Rect is part of the program; include it in your answer.) Sum of w*h over all rectangles.",
 "assert_eq!(total_area(&[]), 0);\nassert_eq!(total_area(&[Rect { w: 2, h: 3 }, Rect { w: 4, h: 5 }]), 26);"),
("collatz", "fn collatz_steps(n: i64) -> i64", "Steps to reach 1: halve if even, else 3n+1. Precondition: n >= 1.",
 "assert_eq!(collatz_steps(1), 0);\nassert_eq!(collatz_steps(6), 8);\nassert_eq!(collatz_steps(27), 111);"),
("digit_sum", "fn digit_sum(n: i64) -> i64", "Sum of decimal digits. Precondition: n >= 0.",
 "assert_eq!(digit_sum(0), 0);\nassert_eq!(digit_sum(12345), 15);\nassert_eq!(digit_sum(1000), 1);"),
("count_unique", "fn count_unique(xs: &[i64]) -> i64", "Number of distinct values in xs (unsorted, any order).",
 "assert_eq!(count_unique(&[]), 0);\nassert_eq!(count_unique(&[1, 1, 1]), 1);\nassert_eq!(count_unique(&[3, 1, 3, 2, 1]), 3);"),
# v0.2 counterparts
("safe_div", "fn safe_div(a: i64, b: i64) -> Result<i64, String>",
 "Err(\"division by zero\") if b == 0; Err(\"overflow\") if a is i64::MIN and b == -1; otherwise Ok(a / b).",
 "assert_eq!(safe_div(7, 2), Ok(3));\nassert_eq!(safe_div(-7, 2), Ok(-3));\n"
 "assert_eq!(safe_div(1, 0), Err(\"division by zero\".to_string()));\n"
 "assert_eq!(safe_div(-9223372036854775808, -1), Err(\"overflow\".to_string()));\n"
 "assert_eq!(safe_div(-9223372036854775808, 1), Ok(-9223372036854775808));"),
("find_index", "fn find_index(xs: &[i64], t: i64) -> Option<i64>", "Index of the first element equal to t, or None.",
 "assert_eq!(find_index(&[], 1), None);\nassert_eq!(find_index(&[4, 7, 7], 7), Some(1));\nassert_eq!(find_index(&[4, 7], 5), None);"),
("min_pos", "fn min_pos(xs: &[i64]) -> Option<i64>", "Smallest element that is > 0, or None if there is none.",
 "assert_eq!(min_pos(&[]), None);\nassert_eq!(min_pos(&[-1, 0]), None);\nassert_eq!(min_pos(&[5, -3, 2, 9]), Some(2));"),
("mean_checked", "fn mean_checked(xs: &[f64]) -> Result<f64, String>", "Arithmetic mean; Err(\"empty\") for an empty slice.",
 "assert_eq!(mean_checked(&[]), Err(\"empty\".to_string()));\nassert_eq!(mean_checked(&[1.0, 2.0]), Ok(1.5));"),
("checked_sum", "fn checked_sum(xs: &[i64]) -> Result<i64, String>",
 "Sum of the elements; Err(\"overflow\") if the sum (or any partial sum, left to right) does not fit in i64. Must not panic.",
 "assert_eq!(checked_sum(&[]), Ok(0));\nassert_eq!(checked_sum(&[1, 2, 3]), Ok(6));\n"
 "assert_eq!(checked_sum(&[9223372036854775807, 1]), Err(\"overflow\".to_string()));\n"
 "assert_eq!(checked_sum(&[-9223372036854775807, -1, -1]), Err(\"overflow\".to_string()));\n"
 "assert_eq!(checked_sum(&[9223372036854775807, -1, 1]), Ok(9223372036854775807));"),
("classify", D + "enum Tri { Equilateral, Isosceles, Scalene, Invalid }\n\nfn classify(a: i64, b: i64, c: i64) -> Tri",
 "(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths "
 "(each below 1000000000). Invalid if any side <= 0 or the two shorter sides sum to <= the longest.",
 "assert_eq!(classify(3, 3, 3), Tri::Equilateral);\nassert_eq!(classify(3, 3, 5), Tri::Isosceles);\n"
 "assert_eq!(classify(5, 3, 3), Tri::Isosceles);\nassert_eq!(classify(3, 4, 5), Tri::Scalene);\n"
 "assert_eq!(classify(1, 2, 3), Tri::Invalid);\nassert_eq!(classify(0, 1, 1), Tri::Invalid);"),
("light", D + "enum Light { Red, Green, Yellow }\n\nfn after(l: Light, n: i64) -> Light",
 "(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle "
 "Red -> Green -> Yellow -> Red. Precondition: n >= 0. n can be up to 10^18.",
 "assert_eq!(after(Light::Red, 0), Light::Red);\nassert_eq!(after(Light::Red, 1), Light::Green);\n"
 "assert_eq!(after(Light::Green, 2), Light::Red);\nassert_eq!(after(Light::Yellow, 1000000000000000000), Light::Red);"),
("bank", D + "enum Tx { Deposit(i64), Withdraw(i64) }\n\nfn apply(balance: i64, txs: &[Tx]) -> Result<i64, String>",
 "(The enum Tx is part of the program; include it in your answer.) Apply transactions in order, return the final "
 "balance. Err(\"invalid amount\") for an amount <= 0; Err(\"insufficient funds\") if a withdrawal exceeds the "
 "current balance. Stop at the first error. Amounts and balances stay below 10^15.",
 "assert_eq!(apply(10, &[]), Ok(10));\nassert_eq!(apply(0, &[Tx::Deposit(5), Tx::Withdraw(3)]), Ok(2));\n"
 "assert_eq!(apply(0, &[Tx::Withdraw(1), Tx::Deposit(0)]), Err(\"insufficient funds\".to_string()));\n"
 "assert_eq!(apply(5, &[Tx::Deposit(0)]), Err(\"invalid amount\".to_string()));"),
("stack_calc", D + "enum Op { Push(i64), Add, Mul, Neg }\n\nfn calc(ops: &[Op]) -> Result<i64, String>",
 "(The enum Op is part of the program; include it in your answer.) Run a stack machine: Push puts a value; "
 "Add and Mul pop two values and push the result; Neg negates the top. Err(\"underflow\") if an op lacks operands; "
 "at the end return the top of the stack, or Err(\"empty\") if the stack is empty. Values stay small.",
 "assert_eq!(calc(&[]), Err(\"empty\".to_string()));\n"
 "assert_eq!(calc(&[Op::Push(2), Op::Push(3), Op::Add, Op::Push(4), Op::Mul]), Ok(20));\n"
 "assert_eq!(calc(&[Op::Push(2), Op::Neg]), Ok(-2));\n"
 "assert_eq!(calc(&[Op::Push(1), Op::Add]), Err(\"underflow\".to_string()));\n"
 "assert_eq!(calc(&[Op::Neg]), Err(\"underflow\".to_string()));"),
("last_or", "fn last_or<T: Clone>(xs: &[T], d: T) -> T", "Generic: the last element of xs, or d if xs is empty.",
 "assert_eq!(last_or(&[1, 2, 3], 0), 3);\nlet e: Vec<i64> = vec![];\nassert_eq!(last_or(&e, 7), 7);\n"
 "assert_eq!(last_or(&[\"a\", \"b\"], \"z\"), \"b\");"),
]

root = pathlib.Path(__file__).parent / "tasks"
for name, sig, desc, tests in T:
    d = root / name
    assert d.is_dir(), name
    (d / "task.rs.md").write_text(f"Write this Rust (edition 2021, std only) definition (name and signature exactly):\n\n"
                                  f"```rust\n{sig}\n```\n\n{desc}\n")
    body = "\n".join("    " + l for l in tests.splitlines())
    (d / "tests.rs").write_text(f"#[test]\nfn test_ref_{name}() {{\n{body}\n}}\n")
