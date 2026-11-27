Write this Python 3.12 definition (name and signature exactly):

```python
def hist(xs: list[int], lo: int, hi: int, n: int) -> list[int]
```

Histogram with n bins of equal width w = (hi - lo) / n: bin i counts the values v with lo + i*w <= v < lo + (i+1)*w. Values outside [lo, hi) are ignored. Return the n counts. Precondition: n >= 1, lo < hi, (hi - lo) divisible by n, |lo| and |hi| below 10^15.
