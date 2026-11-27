#[test]
fn test_ref_transfer_all() {
    let mut b0 = vec![10, 0, 0];
    assert_eq!(transfer_all(&mut b0, &[Transfer { src: 0, dst: 1, amt: 5 }, Transfer { src: 1, dst: 2, amt: 5 }]), Ok(2));
    assert_eq!(b0, vec![5, 0, 5]);
    let mut b1 = vec![10, 0, 0];
    assert_eq!(transfer_all(&mut b1, &[]), Ok(0));
    assert_eq!(b1, vec![10, 0, 0]);
    let mut b2 = vec![10, 0, 0];
    assert_eq!(transfer_all(&mut b2, &[Transfer { src: 0, dst: 1, amt: 5 }, Transfer { src: 1, dst: 2, amt: 6 }]), Err("insufficient funds".to_string()));
    assert_eq!(b2, vec![10, 0, 0]);
    let mut b3 = vec![10, 0, 0];
    assert_eq!(transfer_all(&mut b3, &[Transfer { src: 0, dst: 1, amt: 5 }, Transfer { src: 0, dst: 2, amt: 5 }, Transfer { src: 2, dst: 3, amt: 1 }]), Err("bad account".to_string()));
    assert_eq!(b3, vec![10, 0, 0]);
    let mut b4 = vec![10, 0];
    assert_eq!(transfer_all(&mut b4, &[Transfer { src: 0, dst: 1, amt: 4 }, Transfer { src: 1, dst: 0, amt: 4 }, Transfer { src: 0, dst: 1, amt: 0 }]), Err("bad amount".to_string()));
    assert_eq!(b4, vec![10, 0]);
}
