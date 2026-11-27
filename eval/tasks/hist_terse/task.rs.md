Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn hist(xs: &[i64], lo: i64, hi: i64, n: i64) -> Vec<i64>
```

Histogram of xs over [lo, hi) with n bins of equal width; return the n counts. Precondition: n >= 1, lo < hi, hi - lo divisible by n.
