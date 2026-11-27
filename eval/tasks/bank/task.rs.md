Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
enum Tx { Deposit(i64), Withdraw(i64) }

fn apply(balance: i64, txs: &[Tx]) -> Result<i64, String>
```

(The enum Tx is part of the program; include it in your answer.) Apply transactions in order, return the final balance. Err("invalid amount") for an amount <= 0; Err("insufficient funds") if a withdrawal exceeds the current balance. Stop at the first error. Amounts and balances stay below 10^15.
