def test_ref_sum_array():
    assert sum_array([]) == 0
    assert sum_array([1, 2, 3]) == 6
    assert sum_array([-5, 5, 7]) == 7
