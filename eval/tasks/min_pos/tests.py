def test_ref_min_pos():
    assert min_pos([]) is None
    assert min_pos([-1, 0]) is None
    assert min_pos([5, -3, 2, 9]) == 2
