#[test]
fn test_ref_last_or() {
    assert_eq!(last_or(&[1, 2, 3], 0), 3);
    let e: Vec<i64> = vec![];
    assert_eq!(last_or(&e, 7), 7);
    assert_eq!(last_or(&["a", "b"], "z"), "b");
}
