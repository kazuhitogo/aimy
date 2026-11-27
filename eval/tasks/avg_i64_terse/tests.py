def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_avg_i64():
    err(lambda: avg_i64([]), "empty")
    assert avg_i64([1, 2]) == 1
    assert avg_i64([-1, -2]) == -1
    assert avg_i64([7, -2]) == 2
    assert avg_i64([-7, 2]) == -2
    assert avg_i64([9223372036854775807, 9223372036854775807, 9223372036854775807]) == 9223372036854775807
    assert avg_i64([-9223372036854775808, -9223372036854775808]) == -9223372036854775808
    assert avg_i64([9223372036854775807, -9223372036854775808]) == 0
    assert avg_i64([9223372036854775807, 9223372036854775807, -9223372036854775807]) == 3074457345618258602
    assert avg_i64([-9223372036854775808, -9223372036854775808, 1]) == -6148914691236517205
