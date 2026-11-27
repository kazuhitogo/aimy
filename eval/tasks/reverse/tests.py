def test_ref_reverse():
    assert reverse([]) == []
    a = [1, 2, 3]
    assert reverse(a) == [3, 2, 1]
    assert a == [1, 2, 3]
