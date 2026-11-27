Write this Python 3.12 definition (name and signature exactly):

```python
def transfer(bal: list[int], src: int, dst: int, amt: int) -> int
```

Move amt from bal[src] to bal[dst] and return the new balance of bal[src]. Errors, checked in this order: raise ValueError("bad account") if src or dst is not an account; raise ValueError("bad amount") if amt <= 0; raise ValueError("insufficient funds") if bal[src] < amt.
