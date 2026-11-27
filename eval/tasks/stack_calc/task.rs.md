Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
enum Op { Push(i64), Add, Mul, Neg }

fn calc(ops: &[Op]) -> Result<i64, String>
```

(The enum Op is part of the program; include it in your answer.) Run a stack machine: Push puts a value; Add and Mul pop two values and push the result; Neg negates the top. Err("underflow") if an op lacks operands; at the end return the top of the stack, or Err("empty") if the stack is empty. Values stay small.
