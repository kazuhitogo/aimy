Write this aimy definition (name and signature exactly):

```
fn safe_div(a: i64, b: i64) -> Result[i64]
```

Err("division by zero") if b == 0; Err("overflow") if a is the smallest i64 and b == -1; otherwise Ok(a / b).
