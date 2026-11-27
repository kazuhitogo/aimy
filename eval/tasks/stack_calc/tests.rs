#[test]
fn test_ref_stack_calc() {
    assert_eq!(calc(&[]), Err("empty".to_string()));
    assert_eq!(calc(&[Op::Push(2), Op::Push(3), Op::Add, Op::Push(4), Op::Mul]), Ok(20));
    assert_eq!(calc(&[Op::Push(2), Op::Neg]), Ok(-2));
    assert_eq!(calc(&[Op::Push(1), Op::Add]), Err("underflow".to_string()));
    assert_eq!(calc(&[Op::Neg]), Err("underflow".to_string()));
}
