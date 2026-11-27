def test_ref_last_or():
    assert last_or([1, 2, 3], 0) == 3
    assert last_or([], 7) == 7
    assert last_or(["a", "b"], "z") == "b"
