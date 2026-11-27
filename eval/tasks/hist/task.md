Write this aimy definition (name and signature exactly):

```
fn hist(xs: [i64], lo: i64, hi: i64, n: i64) -> [i64]
  requires n >= 1 and lo < hi
```

Histogram with n bins of equal width w = (hi - lo) / n: bin i counts the values v with lo + i*w <= v < lo + (i+1)*w. Values outside [lo, hi) are ignored. Return the n counts. Precondition: n >= 1, lo < hi, (hi - lo) divisible by n, |lo| and |hi| below 10^15.
