def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_transfer_all():
    b = [10, 0, 0]
    assert transfer_all(b, [Transfer(0, 1, 5), Transfer(1, 2, 5)]) == 2
    assert b == [5, 0, 5]
    b = [10, 0, 0]
    assert transfer_all(b, []) == 0
    assert b == [10, 0, 0]
    b = [10, 0, 0]
    err(lambda: transfer_all(b, [Transfer(0, 1, 5), Transfer(1, 2, 6)]), "insufficient funds")
    assert b == [10, 0, 0]
    b = [10, 0, 0]
    err(lambda: transfer_all(b, [Transfer(0, 1, 5), Transfer(0, 2, 5), Transfer(2, 3, 1)]), "bad account")
    assert b == [10, 0, 0]
    b = [10, 0]
    err(lambda: transfer_all(b, [Transfer(0, 1, 4), Transfer(1, 0, 4), Transfer(0, 1, 0)]), "bad amount")
    assert b == [10, 0]
