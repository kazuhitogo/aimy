#[test]
fn test_ref_transfer() {
    let mut b0 = vec![10, 5];
    assert_eq!(transfer(&mut b0, 0, 1, 3), Ok(7));
    assert_eq!(b0, vec![7, 8]);
    let mut b1 = vec![10, 5];
    assert_eq!(transfer(&mut b1, 1, 1, 5), Ok(5));
    assert_eq!(b1, vec![10, 5]);
    let mut b2 = vec![10, 5];
    assert_eq!(transfer(&mut b2, 1, 0, 6), Err("insufficient funds".to_string()));
    assert_eq!(b2, vec![10, 5]);
    let mut b3 = vec![10, 5];
    assert_eq!(transfer(&mut b3, 0, 2, 1), Err("bad account".to_string()));
    assert_eq!(b3, vec![10, 5]);
    let mut b4 = vec![10, 5];
    assert_eq!(transfer(&mut b4, -1, 0, 1), Err("bad account".to_string()));
    assert_eq!(b4, vec![10, 5]);
    let mut b5 = vec![10, 5];
    assert_eq!(transfer(&mut b5, 0, -1, 1), Err("bad account".to_string()));
    assert_eq!(b5, vec![10, 5]);
    let mut b6 = vec![10, 5];
    assert_eq!(transfer(&mut b6, 0, 1, 0), Err("bad amount".to_string()));
    assert_eq!(b6, vec![10, 5]);
    let mut b7 = vec![10, 5];
    assert_eq!(transfer(&mut b7, 0, 5, -1), Err("bad account".to_string()));
    assert_eq!(b7, vec![10, 5]);
    let mut b8 = vec![10, 5];
    assert_eq!(transfer(&mut b8, 1, 1, 6), Err("insufficient funds".to_string()));
    assert_eq!(b8, vec![10, 5]);
}
