Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn avg_i64(xs: &[i64]) -> Result<i64, String>
```

The mean of xs rounded toward zero, Err("empty") for an empty input. Must be exact for any i64 values, even when their sum does not fit in i64 (the mean always does). len(xs) stays below 10^6.
