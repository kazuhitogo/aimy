def test_ref_count_unique():
    assert count_unique([]) == 0
    assert count_unique([1, 1, 1]) == 1
    a = [3, 1, 3, 2, 1]
    assert count_unique(a) == 3
    assert a == [3, 1, 3, 2, 1]
