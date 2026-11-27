def test_ref_sort():
    a = [3, 1, 2]
    sort(a)
    assert a == [1, 2, 3]
    b = []
    sort(b)
    assert b == []
    c = [5, 5, -1, 9, 0]
    sort(c)
    assert c == [-1, 0, 5, 5, 9]
