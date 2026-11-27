#[test]
fn test_ref_mean_checked() {
    assert_eq!(mean_checked(&[]), Err("empty".to_string()));
    assert_eq!(mean_checked(&[1.0, 2.0]), Ok(1.5));
}
