def test_ref_find_index():
    assert find_index([], 1) is None
    assert find_index([4, 7, 7], 7) == 1
    assert find_index([4, 7], 5) is None
