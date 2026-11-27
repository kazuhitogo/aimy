Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
enum Tri { Equilateral, Isosceles, Scalene, Invalid }

fn classify(a: i64, b: i64, c: i64) -> Tri
```

(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths (each below 1000000000). Invalid if any side <= 0 or the two shorter sides sum to <= the longest.
