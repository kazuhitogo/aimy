#[test]
fn test_ref_count_unique() {
    assert_eq!(count_unique(&[]), 0);
    assert_eq!(count_unique(&[1, 1, 1]), 1);
    assert_eq!(count_unique(&[3, 1, 3, 2, 1]), 3);
}
