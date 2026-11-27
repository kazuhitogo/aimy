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

(The class Transfer is part of the program; include it in your answer.) Apply the transfers in order as one transaction and return how many were applied. Each moves amt from bal[src] to bal[dst]. Errors, checked in this order for each transfer: raise ValueError("bad account") if src or dst is not an account; raise ValueError("bad amount") if amt <= 0; raise ValueError("insufficient funds") if bal[src] < amt. On an error the result is the first error.
