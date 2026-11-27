#[test]
fn test_ref_is_prime() {
    assert!(!is_prime(-5));
    assert!(!is_prime(1));
    assert!(is_prime(2));
    assert!(is_prime(97));
    assert!(!is_prime(91));
    assert!(is_prime(7919));
}
