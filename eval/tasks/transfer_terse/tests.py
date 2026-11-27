def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_transfer():
    b = [10, 5]
    assert transfer(b, 0, 1, 3) == 7
    assert b == [7, 8]
    b = [10, 5]
    assert transfer(b, 1, 1, 5) == 5
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 1, 0, 6), "insufficient funds")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 0, 2, 1), "bad account")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, -1, 0, 1), "bad account")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 0, -1, 1), "bad account")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 0, 1, 0), "bad amount")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 0, 5, -1), "bad account")
    assert b == [10, 5]
    b = [10, 5]
    err(lambda: transfer(b, 1, 1, 6), "insufficient funds")
    assert b == [10, 5]
