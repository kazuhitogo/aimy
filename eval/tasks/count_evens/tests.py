def test_ref_count_evens():
    assert count_evens([]) == 0
    assert count_evens([1, 2, 4, -6, 7]) == 3
