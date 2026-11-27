def test_ref_rect_area():
    assert total_area([]) == 0
    assert total_area([Rect(2, 3), Rect(4, 5)]) == 26
