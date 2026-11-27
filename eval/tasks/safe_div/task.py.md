Write this Python 3.12 definition (name and signature exactly):

```python
def safe_div(a: int, b: int) -> int
```

Integer division truncating toward zero, on 64-bit signed values. Raise ValueError("division by zero") if b == 0; raise ValueError("overflow") if a is the smallest i64 (-2**63) and b == -1.
