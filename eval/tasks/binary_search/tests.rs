#[test]
fn test_ref_binary_search() {
    assert_eq!(binary_search(&[], 1), -1);
    assert_eq!(binary_search(&[1, 3, 5, 7], 5), 2);
    assert_eq!(binary_search(&[1, 3, 5, 7], 1), 0);
    assert_eq!(binary_search(&[1, 3, 5, 7], 4), -1);
}
