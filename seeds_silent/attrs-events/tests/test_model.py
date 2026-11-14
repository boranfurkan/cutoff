from events import model


def test_refund_fields():
    r = model.refund(7, 250, "duplicate charge")
    assert (r.account_id, r.amount_pence, r.reason) == (7, 250, "duplicate charge")


def test_to_row():
    assert model.to_row(model.refund(7, 250)) == {"account_id": 7, "amount_pence": 250, "reason": "unspecified"}


def test_event_positional():
    assert model.Event(1, 2).amount_pence == 2
