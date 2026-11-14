import pytest

from events import model


def test_refund_rejects_positional_arguments():
    with pytest.raises(TypeError):
        model.Refund(250, 7)


def test_refund_by_keyword_still_works():
    assert model.Refund(account_id=7, amount_pence=250).amount_pence == 250
