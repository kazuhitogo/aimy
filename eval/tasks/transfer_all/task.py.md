Write this Python 3.12 definition (name and signature exactly):

```python
from dataclasses import dataclass

@dataclass
class Transfer:
    src: int
    dst: int
    amt: int

def transfer_all(bal: list[int], ts: list[Transfer]) -> int
```

(The class Transfer is part of the program; include it in your answer.) Apply the transfers in order. Each one follows these rules: Move amt from bal[src] to bal[dst]. Checks, in this order: raise ValueError("bad account") if src or dst is not a valid index; raise ValueError("bad amount") if amt <= 0; raise ValueError("insufficient funds") if bal[src] < amt. src == dst is allowed (same checks, balances unchanged). Balances and amounts stay below 10^15. All or nothing: if any transfer fails, bal must end exactly as it was before the call and the result is that transfer's error; otherwise return the number of transfers applied.
