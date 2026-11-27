Write this aimy definition (name and signature exactly):

```
enum Tri { Equilateral, Isosceles, Scalene, Invalid } end Tri

fn classify(a: i64, b: i64, c: i64) -> Tri
```

(The enum Tri is part of the program; include it in your answer.) Triangle kind from side lengths (each below 1000000000). Invalid if any side <= 0 or the two shorter sides sum to <= the longest.
