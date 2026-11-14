"""Order models and settings."""
from typing import List, Optional

from pydantic import BaseModel, BaseSettings, Field, root_validator, validator


class Settings(BaseSettings):
    currency: str = "GBP"

    class Config:
        env_prefix = "SHOP_"


class Line(BaseModel):
    sku: str = Field(..., regex=r"^[A-Z]{3}\d+$")
    qty: int = Field(1, gt=0)
    note: Optional[str]

    class Config:
        orm_mode = True

    @validator("sku", pre=True)
    def upper(cls, v):
        return v.upper()


class Order(BaseModel):
    id: int
    lines: List[Line] = Field(..., min_items=1)
    total_qty: int = 0

    class Config:
        allow_mutation = False
        orm_mode = True

    @root_validator
    def compute_total(cls, values):
        values["total_qty"] = sum(l.qty for l in values.get("lines", []))
        return values


def parse_order(data):
    return Order.parse_obj(data)


def to_json(order):
    return order.json()


def field_names():
    return list(Order.__fields__)


def clone(order, **changes):
    return order.copy(update=changes)


def from_row(row):
    return Order.from_orm(row)
