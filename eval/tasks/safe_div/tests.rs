#[test]
fn test_ref_safe_div() {
    assert_eq!(safe_div(7, 2), Ok(3));
    assert_eq!(safe_div(-7, 2), Ok(-3));
    assert_eq!(safe_div(1, 0), Err("division by zero".to_string()));
    assert_eq!(safe_div(-9223372036854775808, -1), Err("overflow".to_string()));
    assert_eq!(safe_div(-9223372036854775808, 1), Ok(-9223372036854775808));
}
