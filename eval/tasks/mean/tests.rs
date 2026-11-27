#[test]
fn test_ref_mean() {
    assert_eq!(mean(&[2.0, 4.0]), 3.0);
    assert_eq!(mean(&[5.0]), 5.0);
}
