def test_ref_light():
    assert after(Light.RED, 0) == Light.RED
    assert after(Light.RED, 1) == Light.GREEN
    assert after(Light.GREEN, 2) == Light.RED
    assert after(Light.YELLOW, 1000000000000000000) == Light.RED
