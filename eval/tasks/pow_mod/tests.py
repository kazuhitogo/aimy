def test_ref_pow_mod():
    assert pow_mod(2, 10, 1000) == 24
    assert pow_mod(3, 0, 7) == 1
    assert pow_mod(2, 100, 1000000007) == 976371285
    assert pow_mod(999999999, 999999999, 1000000000) == 999999999
