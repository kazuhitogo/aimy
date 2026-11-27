def test_ref_classify():
    assert classify(3, 3, 3) == Tri.EQUILATERAL
    assert classify(3, 3, 5) == Tri.ISOSCELES
    assert classify(5, 3, 3) == Tri.ISOSCELES
    assert classify(3, 4, 5) == Tri.SCALENE
    assert classify(1, 2, 3) == Tri.INVALID
    assert classify(0, 1, 1) == Tri.INVALID
