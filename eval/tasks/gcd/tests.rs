#[test]
fn test_ref_gcd() {
    assert_eq!(gcd(12, 18), 6);
    assert_eq!(gcd(7, 0), 7);
    assert_eq!(gcd(0, 0), 0);
    assert_eq!(gcd(17, 13), 1);
}
