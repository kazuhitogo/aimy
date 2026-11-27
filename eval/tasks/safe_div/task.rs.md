Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn safe_div(a: i64, b: i64) -> Result<i64, String>
```

Err("division by zero") if b == 0; Err("overflow") if a is i64::MIN and b == -1; otherwise Ok(a / b).
