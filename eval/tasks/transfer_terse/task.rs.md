Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn transfer(bal: &mut [i64], src: i64, dst: i64, amt: i64) -> Result<i64, String>
```

Move amt from bal[src] to bal[dst] and return the new balance of bal[src]. Errors, checked in this order: Err("bad account") if src or dst is not an account; Err("bad amount") if amt <= 0; Err("insufficient funds") if bal[src] < amt.
