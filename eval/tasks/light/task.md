Write this aimy definition (name and signature exactly):

```
enum Light { Red, Green, Yellow } end Light

fn after(l: Light, n: i64) -> Light
  requires n >= 0
```

(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle Red -> Green -> Yellow -> Red. n can be up to 10^18.
