Write this Python 3.12 definition (name and signature exactly):

```python
from enum import Enum

class Tri(Enum):
    EQUILATERAL = 1
    ISOSCELES = 2
    SCALENE = 3
    INVALID = 4

def classify(a: int, b: int, c: int) -> Tri
```

(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths (each below 1000000000). INVALID if any side <= 0 or the two shorter sides sum to <= the longest.
