Write this Python 3.12 definition (name and signature exactly):

```python
from dataclasses import dataclass

@dataclass
class Deposit:
    amount: int

@dataclass
class Withdraw:
    amount: int

Tx = Deposit | Withdraw

def apply(balance: int, txs: list[Tx]) -> int
```

(The classes Deposit, Withdraw and the alias Tx are part of the program; include them in your answer.) Apply transactions in order, return the final balance. Raise ValueError("invalid amount") for an amount <= 0; raise ValueError("insufficient funds") if a withdrawal exceeds the current balance. Stop at the first error.
