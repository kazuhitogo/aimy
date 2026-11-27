#[test]
fn test_ref_min_pos() {
    assert_eq!(min_pos(&[]), None);
    assert_eq!(min_pos(&[-1, 0]), None);
    assert_eq!(min_pos(&[5, -3, 2, 9]), Some(2));
}
