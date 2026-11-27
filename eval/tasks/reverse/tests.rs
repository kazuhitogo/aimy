#[test]
fn test_ref_reverse() {
    assert_eq!(reverse(&[]), Vec::<i64>::new());
    assert_eq!(reverse(&[1, 2, 3]), vec![3, 2, 1]);
}
