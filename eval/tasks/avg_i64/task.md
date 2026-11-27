Write this aimy definition (name and signature exactly):

```
fn avg_i64(xs: [i64]) -> Result[i64]
```

The mean of xs rounded toward zero, Err("empty") for an empty input. Must be exact for any i64 values, even when their sum does not fit in i64 (the mean always does). len(xs) stays below 10^6.
