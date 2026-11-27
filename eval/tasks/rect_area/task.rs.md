Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
struct Rect { w: i64, h: i64 }

fn total_area(rs: &[Rect]) -> i64
```

(The struct Rect is part of the program; include it in your answer.) Sum of w*h over all rectangles.
