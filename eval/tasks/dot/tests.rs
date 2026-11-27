#[test]
fn test_ref_dot() {
    assert_eq!(dot(&[], &[]), 0.0);
    assert_eq!(dot(&[1.0, 2.0, 3.0], &[4.0, 5.0, 6.0]), 32.0);
}
