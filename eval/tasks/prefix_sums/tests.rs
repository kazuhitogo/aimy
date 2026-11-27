#[test]
fn test_ref_prefix_sums() {
    assert_eq!(prefix_sums(&[]), Vec::<i64>::new());
    assert_eq!(prefix_sums(&[1, 2, 3, 4]), vec![1, 3, 6, 10]);
}
