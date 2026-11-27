Write this aimy definition (name and signature exactly):

```
fn hist(xs: [i64], lo: i64, hi: i64, n: i64) -> [i64]
  requires n >= 1 and lo < hi
```

Histogram of xs over [lo, hi) with n bins of equal width; return the n counts.
