Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn local_peaks(xs: &[i64]) -> i64
```

Count the indices i where xs[i] is strictly greater than each neighbor that exists (xs[i-1] and xs[i+1]; the first and last elements have only one neighbor, a single element has none).
