#[test]
fn test_ref_rect_area() {
    assert_eq!(total_area(&[]), 0);
    assert_eq!(total_area(&[Rect { w: 2, h: 3 }, Rect { w: 4, h: 5 }]), 26);
}
