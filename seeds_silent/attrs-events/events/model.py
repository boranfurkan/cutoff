"""Billing event records."""
from attrs import asdict, define


@define
class Event:
    account_id: int
    amount_pence: int


@define(kw_only=True)
class Refund(Event):
    """A refund. Every field must be passed by keyword.

    account_id and amount_pence are both integers, so a positional call with the two swapped would
    refund the wrong amount to the wrong account without any error. kw_only makes that impossible.
    """
    reason: str = "unspecified"


def refund(account_id, amount_pence, reason="unspecified"):
    return Refund(account_id=account_id, amount_pence=amount_pence, reason=reason)


def to_row(event):
    return asdict(event)
