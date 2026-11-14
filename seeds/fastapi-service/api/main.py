"""Inventory API."""
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Inventory", openapi_prefix="/api")
DB = {}


class Item(BaseModel):
    name: str
    qty: int = 0


@app.on_event("startup")
def seed():
    DB["widget"] = Item(name="widget", qty=3)


@app.get("/items")
def list_items(prefix: str = Query("", regex="^[a-z]*$", example="wi")):
    return [i.dict() for i in DB.values() if i.name.startswith(prefix)]


@app.post("/items")
def add(item: Item):
    DB[item.name] = item
    return item.dict()
