Write this Python 3.12 definition (name and signature exactly):

```python
from enum import Enum

class Light(Enum):
    RED = 1
    GREEN = 2
    YELLOW = 3

def after(l: Light, n: int) -> Light
```

(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle RED -> GREEN -> YELLOW -> RED. Precondition: n >= 0. n can be up to 10**18.
