#[test]
fn test_ref_bank() {
    assert_eq!(apply(10, &[]), Ok(10));
    assert_eq!(apply(0, &[Tx::Deposit(5), Tx::Withdraw(3)]), Ok(2));
    assert_eq!(apply(0, &[Tx::Withdraw(1), Tx::Deposit(0)]), Err("insufficient funds".to_string()));
    assert_eq!(apply(5, &[Tx::Deposit(0)]), Err("invalid amount".to_string()));
}
