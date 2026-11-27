Write this Python 3.12 definition (name and signature exactly):

```python
def rotate(xs: list[int], k: int) -> None
```

Rotate xs right by k places in place: the element at index i moves to index (i + k) mod len. k can be any i64, including negative (rotate left) and larger than len. An empty xs stays empty.
