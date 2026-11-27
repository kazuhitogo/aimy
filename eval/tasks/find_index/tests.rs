#[test]
fn test_ref_find_index() {
    assert_eq!(find_index(&[], 1), None);
    assert_eq!(find_index(&[4, 7, 7], 7), Some(1));
    assert_eq!(find_index(&[4, 7], 5), None);
}
