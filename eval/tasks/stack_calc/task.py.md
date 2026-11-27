Write this Python 3.12 definition (name and signature exactly):

```python
from dataclasses import dataclass

@dataclass
class Push:
    value: int

@dataclass
class Add:
    pass

@dataclass
class Mul:
    pass

@dataclass
class Neg:
    pass

Op = Push | Add | Mul | Neg

def calc(ops: list[Op]) -> int
```

(The classes Push, Add, Mul, Neg and the alias Op are part of the program; include them in your answer.) Run a stack machine: Push puts a value; Add and Mul pop two values and push the result; Neg negates the top. Raise ValueError("underflow") if an op lacks operands; at the end return the top of the stack, or raise ValueError("empty") if the stack is empty.
