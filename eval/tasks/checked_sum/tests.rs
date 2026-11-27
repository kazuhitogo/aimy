#[test]
fn test_ref_checked_sum() {
    assert_eq!(checked_sum(&[]), Ok(0));
    assert_eq!(checked_sum(&[1, 2, 3]), Ok(6));
    assert_eq!(checked_sum(&[9223372036854775807, 1]), Err("overflow".to_string()));
    assert_eq!(checked_sum(&[-9223372036854775807, -1, -1]), Err("overflow".to_string()));
    assert_eq!(checked_sum(&[9223372036854775807, -1, 1]), Ok(9223372036854775807));
}
