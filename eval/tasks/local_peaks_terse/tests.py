def test_ref_local_peaks():
    assert local_peaks([]) == 0
    assert local_peaks([5]) == 1
    assert local_peaks([1, 2]) == 1
    assert local_peaks([2, 1, 2]) == 2
    assert local_peaks([1, 3, 2, 4, 1]) == 2
    assert local_peaks([3, 3]) == 0
    assert local_peaks([1, 2, 1, 2]) == 2
    assert local_peaks([2, 1, 1, 2]) == 2
