Write this aimy definition (name and signature exactly):

```
struct Transfer { src: i64, dst: i64, amt: i64 } end Transfer

fn transfer_all(mut bal: [i64], ts: [Transfer]) -> Result[i64]
```

(The struct Transfer is part of the program; include it in your answer.) Apply the transfers in order. Each one follows these rules: Move amt from bal[src] to bal[dst]. Checks, in this order: Err("bad account") if src or dst is not a valid index; Err("bad amount") if amt <= 0; Err("insufficient funds") if bal[src] < amt. src == dst is allowed (same checks, balances unchanged). Balances and amounts stay below 10^15. All or nothing: if any transfer fails, bal must end exactly as it was before the call and the result is that transfer's error; otherwise return the number of transfers applied.
