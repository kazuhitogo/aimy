def test_ref_identity():
    assert identity(0) == []
    assert identity(1) == [[1]]
    assert identity(3) == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    g = identity(2)
    g[0][1] = 5
    assert g[1][1] == 1 and g[1][0] == 0
