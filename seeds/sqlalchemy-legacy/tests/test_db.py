from store import db


def setup():
    engine = db.make_engine()
    session = db.add_users(engine, ["bo", "al"])
    return engine, session


def test_count():
    engine, _ = setup()
    assert db.count(engine) == 2


def test_names():
    engine, _ = setup()
    assert db.names(engine) == ["al", "bo"]


def test_get():
    _, session = setup()
    assert db.get(session, 1).name == "bo"


def test_upgrade():
    engine, session = setup()
    db.upgrade(engine, "al")
    session.expire_all()
    assert db.get(session, 2).plan == "pro"
