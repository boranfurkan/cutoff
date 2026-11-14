import json
from types import SimpleNamespace

import pytest

from models import schema


def order():
    return schema.parse_order({"id": 1, "lines": [{"sku": "abc12", "qty": 2}, {"sku": "XYZ1"}]})


def test_parse_and_total():
    o = order()
    assert o.lines[0].sku == "ABC12" and o.lines[0].note is None and o.total_qty == 3


def test_json():
    assert json.loads(schema.to_json(order()))["total_qty"] == 3


def test_fields():
    assert schema.field_names() == ["id", "lines", "total_qty"]


def test_immutable():
    with pytest.raises(Exception):
        order().id = 5


def test_clone():
    assert schema.clone(order(), id=9).id == 9


def test_bad_sku():
    with pytest.raises(ValueError):
        schema.parse_order({"id": 1, "lines": [{"sku": "nope"}]})


def test_settings(monkeypatch):
    monkeypatch.setenv("SHOP_CURRENCY", "EUR")
    assert schema.Settings().currency == "EUR"


def test_from_row():
    row = SimpleNamespace(id=4, lines=[SimpleNamespace(sku="ABC1", qty=1, note=None)], total_qty=0)
    assert schema.from_row(row).total_qty == 1
