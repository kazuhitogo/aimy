Write this Python 3.12 definition (name and signature exactly):

```python
def avg_i64(xs: list[int]) -> int
```

The mean of xs rounded toward zero, raise ValueError("empty") for an empty input. Must be exact for any i64 values, even when their sum does not fit in i64 (the mean always does). len(xs) stays below 10^6.
