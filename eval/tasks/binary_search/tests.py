def test_ref_binary_search():
    assert binary_search([], 1) == -1
    assert binary_search([1, 3, 5, 7], 5) == 2
    assert binary_search([1, 3, 5, 7], 1) == 0
    assert binary_search([1, 3, 5, 7], 4) == -1
