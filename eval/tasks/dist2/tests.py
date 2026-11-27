def test_ref_dist2():
    assert dist2(Point(0, 0), Point(3, 4)) == 25
    assert dist2(Point(-1, -1), Point(-1, -1)) == 0
