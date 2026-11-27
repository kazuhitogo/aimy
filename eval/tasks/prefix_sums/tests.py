def test_ref_prefix_sums():
    assert prefix_sums([]) == []
    assert prefix_sums([1, 2, 3, 4]) == [1, 3, 6, 10]
