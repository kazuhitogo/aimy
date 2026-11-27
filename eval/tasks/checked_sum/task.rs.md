Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn checked_sum(xs: &[i64]) -> Result<i64, String>
```

Sum of the elements; Err("overflow") if the sum (or any partial sum, left to right) does not fit in i64. Must not panic.
