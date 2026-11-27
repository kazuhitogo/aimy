def test_ref_rotate():
    a = [1, 2, 3, 4, 5]
    rotate(a, 2)
    assert a == [4, 5, 1, 2, 3]
    a = [1, 2, 3, 4, 5]
    rotate(a, -1)
    assert a == [2, 3, 4, 5, 1]
    a = [1, 2, 3, 4, 5]
    rotate(a, 7)
    assert a == [4, 5, 1, 2, 3]
    a = [1, 2, 3]
    rotate(a, 0)
    assert a == [1, 2, 3]
    a = [1, 2, 3, 4, 5]
    rotate(a, -9223372036854775808)
    assert a == [4, 5, 1, 2, 3]
    a = [1, 2, 3, 4, 5]
    rotate(a, 9223372036854775807)
    assert a == [4, 5, 1, 2, 3]
    e = []
    rotate(e, 3)
    assert e == []
