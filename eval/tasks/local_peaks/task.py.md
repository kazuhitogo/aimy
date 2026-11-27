Write this Python 3.12 definition (name and signature exactly):

```python
def local_peaks(xs: list[int]) -> int
```

Count the indices i where xs[i] is strictly greater than each neighbor that exists (xs[i-1] and xs[i+1]; the first and last elements have only one neighbor, a single element has none).
