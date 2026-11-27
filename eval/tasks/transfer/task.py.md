Write this Python 3.12 definition (name and signature exactly):

```python
def transfer(bal: list[int], src: int, dst: int, amt: int) -> int
```

Move amt from bal[src] to bal[dst]. Checks, in this order: raise ValueError("bad account") if src or dst is not a valid index; raise ValueError("bad amount") if amt <= 0; raise ValueError("insufficient funds") if bal[src] < amt. src == dst is allowed (same checks, balances unchanged). Balances and amounts stay below 10^15. On success return the new balance of bal[src]. On an error bal must be unchanged.
