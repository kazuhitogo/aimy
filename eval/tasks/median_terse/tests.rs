#[test]
fn test_ref_median() {
    assert_eq!(median(&[3, 1, 2]), 2.0);
    assert_eq!(median(&[4, 1, 3, 2]), 2.5);
    assert_eq!(median(&[5]), 5.0);
    assert_eq!(median(&[-3, -4]), -3.5);
    assert_eq!(median(&[9223372036854775807, 9223372036854775807]), 9223372036854775807.0);
    assert_eq!(median(&[-9223372036854775808, -9223372036854775808, 0, 0]), -4611686018427387904.0);
}
