def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_checked_sum():
    assert checked_sum([]) == 0
    assert checked_sum([1, 2, 3]) == 6
    err(lambda: checked_sum([9223372036854775807, 1]), "overflow")
    err(lambda: checked_sum([-9223372036854775807, -1, -1]), "overflow")
    assert checked_sum([9223372036854775807, -1, 1]) == 9223372036854775807
