Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
enum Light { Red, Green, Yellow }

fn after(l: Light, n: i64) -> Light
```

(The enum Light is part of the program; include it in your answer.) The light after n steps of the cycle Red -> Green -> Yellow -> Red. Precondition: n >= 0. n can be up to 10^18.
