Write this Python 3.12 definition (name and signature exactly):

```python
def checked_sum(xs: list[int]) -> int
```

Sum of the elements; raise ValueError("overflow") if the sum (or any partial sum, left to right) is outside the i64 range -2**63 ..= 2**63-1.
