#[test]
fn test_ref_sum_array() {
    assert_eq!(sum_array(&[]), 0);
    assert_eq!(sum_array(&[1, 2, 3]), 6);
    assert_eq!(sum_array(&[-5, 5, 7]), 7);
}
