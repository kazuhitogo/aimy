#[test]
fn test_ref_hist() {
    assert_eq!(hist(&[0, 1, 2, 3, 9, 10, -1], 0, 10, 5), vec![2, 2, 0, 0, 1]);
    assert_eq!(hist(&[-10, -6, -5, -1, 0, 5], -10, 0, 2), vec![2, 2]);
    assert_eq!(hist(&[], 0, 4, 2), vec![0, 0]);
    assert_eq!(hist(&[-1, -2, -3, 3], 0, 3, 3), vec![0, 0, 0]);
    assert_eq!(hist(&[-7, -4, -3, 2], -6, 3, 3), vec![1, 1, 1]);
}
