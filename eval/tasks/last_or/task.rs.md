Write this Rust (edition 2021, std only) definition (name and signature exactly):

```rust
fn last_or<T: Clone>(xs: &[T], d: T) -> T
```

Generic: the last element of xs, or d if xs is empty.
