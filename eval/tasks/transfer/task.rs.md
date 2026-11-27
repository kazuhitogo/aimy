Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn transfer(bal: &mut [i64], src: i64, dst: i64, amt: i64) -> Result<i64, String>
```

Move amt from bal[src] to bal[dst]. Checks, in this order: Err("bad account") if src or dst is not a valid index; Err("bad amount") if amt <= 0; Err("insufficient funds") if bal[src] < amt. src == dst is allowed (same checks, balances unchanged). Balances and amounts stay below 10^15. On success return the new balance of bal[src]. On an error bal must be unchanged.
