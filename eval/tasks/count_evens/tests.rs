#[test]
fn test_ref_count_evens() {
    assert_eq!(count_evens(&[]), 0);
    assert_eq!(count_evens(&[1, 2, 4, -6, 7]), 3);
}
