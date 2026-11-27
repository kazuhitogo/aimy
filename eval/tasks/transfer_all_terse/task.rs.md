Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
struct Transfer { src: i64, dst: i64, amt: i64 }

fn transfer_all(bal: &mut [i64], ts: &[Transfer]) -> Result<i64, String>
```

(The struct Transfer is part of the program; include it in your answer.) Apply the transfers in order as one transaction and return how many were applied. Each moves amt from bal[src] to bal[dst]. Errors, checked in this order for each transfer: Err("bad account") if src or dst is not an account; Err("bad amount") if amt <= 0; Err("insufficient funds") if bal[src] < amt. On an error the result is the first error.
