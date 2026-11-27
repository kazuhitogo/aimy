Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn rotate(xs: &mut [i64], k: i64)
```

Rotate xs right by k places in place: the element at index i moves to index (i + k) mod len. k can be any i64, including negative (rotate left) and larger than len. An empty xs stays empty.
