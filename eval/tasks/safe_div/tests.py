def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_safe_div():
    assert safe_div(7, 2) == 3
    assert safe_div(-7, 2) == -3
    err(lambda: safe_div(1, 0), "division by zero")
    err(lambda: safe_div(-9223372036854775808, -1), "overflow")
    assert safe_div(-9223372036854775808, 1) == -9223372036854775808
