#[test]
fn test_ref_identity() {
    assert_eq!(identity(0), Vec::<Vec<i64>>::new());
    assert_eq!(identity(1), vec![vec![1]]);
    assert_eq!(identity(3), vec![vec![1, 0, 0], vec![0, 1, 0], vec![0, 0, 1]]);
}
