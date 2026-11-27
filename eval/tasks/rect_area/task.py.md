Write this Python 3.12 definition (name and signature exactly):

```python
from dataclasses import dataclass

@dataclass
class Rect:
    w: int
    h: int

def total_area(rs: list[Rect]) -> int
```

(The class Rect is part of the program; include it in your answer.) Sum of w*h over all rectangles.
