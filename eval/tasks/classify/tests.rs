#[test]
fn test_ref_classify() {
    assert_eq!(classify(3, 3, 3), Tri::Equilateral);
    assert_eq!(classify(3, 3, 5), Tri::Isosceles);
    assert_eq!(classify(5, 3, 3), Tri::Isosceles);
    assert_eq!(classify(3, 4, 5), Tri::Scalene);
    assert_eq!(classify(1, 2, 3), Tri::Invalid);
    assert_eq!(classify(0, 1, 1), Tri::Invalid);
}
