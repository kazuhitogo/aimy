#[test]
fn test_ref_max_array() {
    assert_eq!(max_array(&[3]), 3);
    assert_eq!(max_array(&[1, 9, 4]), 9);
    assert_eq!(max_array(&[-3, -1, -2]), -1);
}
