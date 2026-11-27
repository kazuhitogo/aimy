Write this aimy definition (name and signature exactly):

```
enum Op { Push(i64), Add, Mul, Neg } end Op

fn calc(ops: [Op]) -> Result[i64]
```

(The enum Op is part of the program; include it in your answer.) Run a stack machine: Push puts a value; Add and Mul pop two values and push the result; Neg negates the top. Err("underflow") if an op lacks operands; at the end return the top of the stack, or Err("empty") if the stack is empty. Values stay small.
