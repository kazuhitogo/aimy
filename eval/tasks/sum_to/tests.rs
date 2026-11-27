#[test]
fn test_ref_sum_to() {
    assert_eq!(sum_to(0), 0);
    assert_eq!(sum_to(1), 1);
    assert_eq!(sum_to(100), 5050);
}
