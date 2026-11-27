#[test]
fn test_ref_rotate() {
    let mut a0 = vec![1, 2, 3, 4, 5];
    rotate(&mut a0, 2);
    assert_eq!(a0, vec![4, 5, 1, 2, 3]);
    let mut a1 = vec![1, 2, 3, 4, 5];
    rotate(&mut a1, -1);
    assert_eq!(a1, vec![2, 3, 4, 5, 1]);
    let mut a2 = vec![1, 2, 3, 4, 5];
    rotate(&mut a2, 7);
    assert_eq!(a2, vec![4, 5, 1, 2, 3]);
    let mut a3 = vec![1, 2, 3];
    rotate(&mut a3, 0);
    assert_eq!(a3, vec![1, 2, 3]);
    let mut a4 = vec![1, 2, 3, 4, 5];
    rotate(&mut a4, -9223372036854775808);
    assert_eq!(a4, vec![4, 5, 1, 2, 3]);
    let mut a5 = vec![1, 2, 3, 4, 5];
    rotate(&mut a5, 9223372036854775807);
    assert_eq!(a5, vec![4, 5, 1, 2, 3]);
    let mut e: Vec<i64> = vec![];
    rotate(&mut e, 3);
    assert!(e.is_empty());
}
