def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_stack_calc():
    err(lambda: calc([]), "empty")
    assert calc([Push(2), Push(3), Add(), Push(4), Mul()]) == 20
    assert calc([Push(2), Neg()]) == -2
    err(lambda: calc([Push(1), Add()]), "underflow")
    err(lambda: calc([Neg()]), "underflow")
