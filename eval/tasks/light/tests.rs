#[test]
fn test_ref_light() {
    assert_eq!(after(Light::Red, 0), Light::Red);
    assert_eq!(after(Light::Red, 1), Light::Green);
    assert_eq!(after(Light::Green, 2), Light::Red);
    assert_eq!(after(Light::Yellow, 1000000000000000000), Light::Red);
}
