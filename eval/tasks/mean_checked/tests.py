def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_mean_checked():
    err(lambda: mean_checked([]), "empty")
    assert mean_checked([1.0, 2.0]) == 1.5
