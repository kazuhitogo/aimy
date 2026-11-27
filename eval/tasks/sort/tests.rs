#[test]
fn test_ref_sort() {
    let mut a = vec![3, 1, 2];
    sort(&mut a);
    assert_eq!(a, vec![1, 2, 3]);
    let mut b: Vec<i64> = vec![];
    sort(&mut b);
    assert_eq!(b, Vec::<i64>::new());
    let mut c = vec![5, 5, -1, 9, 0];
    sort(&mut c);
    assert_eq!(c, vec![-1, 0, 5, 5, 9]);
}
