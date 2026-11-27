#[test]
fn test_ref_dist2() {
    assert_eq!(dist2(Point { x: 0, y: 0 }, Point { x: 3, y: 4 }), 25);
    assert_eq!(dist2(Point { x: -1, y: -1 }, Point { x: -1, y: -1 }), 0);
}
