def err(f, msg):
    try:
        f()
    except ValueError as e:
        assert str(e) == msg, f"expected ValueError({msg!r}), got ValueError({str(e)!r})"
        return
    raise AssertionError(f"expected ValueError({msg!r}), nothing raised")

def test_ref_bank():
    assert apply(10, []) == 10
    assert apply(0, [Deposit(5), Withdraw(3)]) == 2
    err(lambda: apply(0, [Withdraw(1), Deposit(0)]), "insufficient funds")
    err(lambda: apply(5, [Deposit(0)]), "invalid amount")
