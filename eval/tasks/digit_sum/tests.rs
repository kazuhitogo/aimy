#[test]
fn test_ref_digit_sum() {
    assert_eq!(digit_sum(0), 0);
    assert_eq!(digit_sum(12345), 15);
    assert_eq!(digit_sum(1000), 1);
}
