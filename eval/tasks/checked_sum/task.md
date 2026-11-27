Write this aimy definition (name and signature exactly):

```
fn checked_sum(xs: [i64]) -> Result[i64]
```

Sum of the elements; Err("overflow") if the sum (or any partial sum, left to right) does not fit in i64. Must not trap.
